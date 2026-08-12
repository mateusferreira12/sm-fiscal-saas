import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api, { formatApiErrorDetail, money, downloadFile } from "@/lib/apiClient";
import { PageHeader, StatusBadge } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { ArrowLeft, FilePdf, FileCode, PaperPlaneTilt, XCircle, Info, PencilLine, SealCheck, MagnifyingGlass, EnvelopeSimple } from "@phosphor-icons/react";
import { toast } from "sonner";

function Field({ label, value }) {
  return <div><div className="text-xs uppercase tracking-wider text-slate-500">{label}</div><div className="text-sm font-medium text-slate-800 mt-0.5">{value || "—"}</div></div>;
}

export default function InvoiceDetail() {
  const { id } = useParams();
  const [inv, setInv] = useState(null);
  const [busy, setBusy] = useState(false);
  const [cceOpen, setCceOpen] = useState(false);
  const [cceText, setCceText] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelText, setCancelText] = useState("");
  const [emailOpen, setEmailOpen] = useState(false);
  const [emailAddr, setEmailAddr] = useState("");
  const navigate = useNavigate();

  const load = () => api.get(`/invoices/${id}`).then((r) => setInv(r.data)).catch(() => navigate("/notas"));
  useEffect(() => { load(); }, [id]);

  if (!inv) return <div className="p-8 text-slate-400">Carregando...</div>;
  const t = inv.totais || {};

  const emit = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/invoices/${id}/emit`);
      setInv(data);
      if (data.status === "rejeitada") toast.error(data.motivo);
      else toast.success("Nota processada");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const cancel = async () => {
    const precisaJust = inv.status === "autorizada" && inv.nprot;
    if (precisaJust && cancelText.trim().length < 15) return toast.error("A justificativa deve ter ao menos 15 caracteres");
    setBusy(true);
    try {
      const { data } = await api.post(`/invoices/${id}/cancel`, { justificativa: cancelText.trim() });
      setInv(data); setCancelOpen(false); setCancelText("");
      if (data.status === "cancelada") toast.success("Nota cancelada");
      else toast.error(data.motivo || "Cancelamento não concluído");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const consultar = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/invoices/${id}/consultar`);
      setInv(data); toast.success("Status consultado no SEFAZ");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const enviarEmail = async () => {
    if (!emailAddr || !emailAddr.includes("@")) return toast.error("Informe um e-mail válido");
    setBusy(true);
    try {
      await api.post(`/invoices/${id}/email`, { email: emailAddr });
      setEmailOpen(false); toast.success(`E-mail enviado para ${emailAddr}`);
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const enviarCce = async () => {
    if (cceText.trim().length < 15) return toast.error("A correção deve ter ao menos 15 caracteres");
    setBusy(true);
    try {
      const { data } = await api.post(`/invoices/${id}/cce`, { texto: cceText.trim() });
      setInv(data); setCceOpen(false); setCceText("");
      const last = data.eventos?.[data.eventos.length - 1];
      if (last?.status === "rejeitado") toast.error(last.motivo);
      else toast.success("Carta de correção registrada");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader title={`Nota #${String(inv.numero).padStart(3, "0")}`} subtitle={`Série ${inv.serie} · ${inv.natureza_operacao}`}>
        <Button variant="outline" onClick={() => navigate("/notas")} data-testid="back-button"><ArrowLeft size={18} className="mr-1" /> Voltar</Button>
      </PageHeader>
      <div className="p-8 space-y-6 max-w-5xl">
        <div className="flex items-center justify-between">
          <StatusBadge status={inv.status} />
          <div className="flex gap-2">
            {(inv.status === "rascunho") && (
              <Button onClick={emit} disabled={busy} data-testid="emit-button"><PaperPlaneTilt size={18} className="mr-1" /> {busy ? "Processando..." : "Emitir NF-e"}</Button>
            )}
            {inv.xml && <Button variant="outline" onClick={() => downloadFile(`/invoices/${id}/xml`, `NFe-${inv.numero}.xml`)} data-testid="download-xml-button"><FileCode size={18} className="mr-1" /> XML</Button>}
            <Button variant="outline" onClick={() => downloadFile(`/invoices/${id}/pdf`, `DANFE-${inv.numero}.pdf`, true)} data-testid="download-pdf-button"><FilePdf size={18} className="mr-1" /> DANFE</Button>
            {(inv.status === "autorizada" || inv.status === "pendente") && (
              <Button variant="outline" onClick={() => { setEmailAddr(inv.cliente?.email || ""); setEmailOpen(true); }} data-testid="email-button"><EnvelopeSimple size={18} className="mr-1" /> E-mail</Button>
            )}
            {(inv.status === "pendente" || inv.status === "rejeitada") && inv.chave_acesso && (
              <Button variant="outline" onClick={consultar} disabled={busy} data-testid="consultar-button"><MagnifyingGlass size={18} className="mr-1" /> Consultar Status</Button>
            )}
            {(inv.status === "autorizada" || inv.status === "pendente") && (
              <>
              {inv.status === "autorizada" && (
                <Button variant="outline" onClick={() => setCceOpen(true)} data-testid="cce-button"><PencilLine size={18} className="mr-1" /> Carta de Correção</Button>
              )}
              <Button variant="outline" className="text-red-600" onClick={() => setCancelOpen(true)} data-testid="cancel-button"><XCircle size={18} className="mr-1" /> Cancelar</Button>
              </>
            )}
          </div>
        </div>

        {inv.motivo && (
          <div className="flex gap-2 items-start bg-blue-50 border border-blue-100 rounded-md p-4 text-sm text-slate-700" data-testid="invoice-motivo">
            <Info size={18} className="text-blue-600 mt-0.5 shrink-0" /> <div>{inv.motivo}</div>
          </div>
        )}

        {inv.chave_acesso && (
          <Card className="p-6 border-slate-200">
            <div className="text-xs uppercase tracking-wider text-slate-500 mb-1">Chave de Acesso</div>
            <div className="mono text-sm break-all">{inv.chave_acesso}</div>
            {(inv.nprot || inv.protocolo) && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                <div className="text-xs uppercase tracking-wider text-slate-500 mb-1">Protocolo de Autorização</div>
                <div className="mono text-sm text-emerald-700 font-medium" data-testid="invoice-protocolo">{inv.nprot || inv.protocolo}</div>
              </div>
            )}
          </Card>
        )}

        {inv.eventos && inv.eventos.length > 0 && (
          <Card className="border-slate-200" data-testid="eventos-card">
            <div className="p-6 border-b border-slate-200"><h3 className="text-sm font-semibold text-slate-800">Eventos / Cartas de Correção</h3></div>
            <div className="divide-y divide-slate-100">
              {inv.eventos.map((ev, i) => (
                <div key={i} className="p-6 flex items-start gap-3" data-testid={`evento-${i}`}>
                  <SealCheck size={20} weight="fill" className={ev.status === "registrado" ? "text-emerald-600 mt-0.5" : "text-amber-600 mt-0.5"} />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-800">{ev.tipo} #{ev.sequencia}</span>
                      <span className="text-xs text-slate-400">{(ev.data || "").slice(0, 10)}</span>
                    </div>
                    <p className="text-sm text-slate-600 mt-1">{ev.texto}</p>
                    <p className="text-xs text-slate-400 mt-1">{ev.motivo} {ev.protocolo && `· Protocolo ${ev.protocolo}`}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          <Card className="p-6 border-slate-200 space-y-4">
            <h3 className="text-sm font-semibold text-slate-800">Destinatário</h3>
            <Field label="Nome" value={inv.cliente?.nome} />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Documento" value={inv.cliente?.cpf_cnpj} />
              <Field label="IE" value={inv.cliente?.ie} />
            </div>
            <Field label="Endereço" value={`${inv.cliente?.endereco?.logradouro || ""} ${inv.cliente?.endereco?.numero || ""} - ${inv.cliente?.endereco?.municipio || ""}/${inv.cliente?.endereco?.uf || ""}`} />
          </Card>
          <Card className="p-6 border-slate-200 space-y-3">
            <h3 className="text-sm font-semibold text-slate-800">Totais</h3>
            {[["Produtos", t.v_prod], ["ICMS", t.v_icms], ["IPI", t.v_ipi], ["PIS", t.v_pis], ["COFINS", t.v_cofins]].map(([l, v]) => (
              <div key={l} className="flex justify-between text-sm"><span className="text-slate-500">{l}</span><span className="font-medium">{money(v)}</span></div>
            ))}
            <div className="flex justify-between pt-3 border-t border-slate-100 text-lg font-bold"><span>Total da Nota</span><span className="text-blue-600">{money(t.v_nf)}</span></div>
          </Card>
        </div>

        <Card className="border-slate-200">
          <div className="p-6 border-b border-slate-200"><h3 className="text-sm font-semibold text-slate-800">Itens</h3></div>
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-100">
              <th className="px-6 py-3">Código</th><th className="px-6 py-3">Descrição</th><th className="px-6 py-3">NCM</th><th className="px-6 py-3">CFOP</th>
              <th className="px-6 py-3">Qtd</th><th className="px-6 py-3">Unit.</th><th className="px-6 py-3 text-right">Total</th>
            </tr></thead>
            <tbody>
              {inv.itens?.map((it, i) => (
                <tr key={i} className="border-b border-slate-50">
                  <td className="px-6 py-3 mono">{it.codigo}</td><td className="px-6 py-3">{it.descricao}</td>
                  <td className="px-6 py-3 mono text-slate-500">{it.ncm}</td><td className="px-6 py-3 mono text-slate-500">{it.cfop}</td>
                  <td className="px-6 py-3">{it.quantidade}</td><td className="px-6 py-3">{money(it.valor_unitario)}</td>
                  <td className="px-6 py-3 text-right font-medium">{money(it.valor_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <Dialog open={cceOpen} onOpenChange={setCceOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Carta de Correção Eletrônica (CC-e)</DialogTitle>
            <DialogDescription>Registre uma correção para esta nota autorizada.</DialogDescription></DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-xs text-slate-500">A CC-e não pode alterar valores, impostos, dados do destinatário/remetente ou datas. Mínimo de 15 caracteres.</p>
            <div className="space-y-2">
              <Label>Texto da correção</Label>
              <Textarea rows={4} value={cceText} onChange={(e) => setCceText(e.target.value)} data-testid="cce-text-input" placeholder="Descreva a correção..." />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCceOpen(false)}>Cancelar</Button>
            <Button onClick={enviarCce} disabled={busy} data-testid="submit-cce-button">{busy ? "Enviando..." : "Registrar CC-e"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={cancelOpen} onOpenChange={setCancelOpen}>        <DialogContent>
          <DialogHeader><DialogTitle>Cancelar nota fiscal</DialogTitle>
            <DialogDescription>
              {inv.status === "autorizada" && inv.nprot
                ? "O cancelamento será transmitido ao SEFAZ (evento 110111). Informe a justificativa."
                : "Esta nota será marcada como cancelada."}
            </DialogDescription></DialogHeader>
          {inv.status === "autorizada" && inv.nprot && (
            <div className="space-y-2 py-2">
              <Label>Justificativa (mín. 15 caracteres)</Label>
              <Textarea rows={3} value={cancelText} onChange={(e) => setCancelText(e.target.value)} data-testid="cancel-text-input" placeholder="Motivo do cancelamento..." />
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelOpen(false)}>Voltar</Button>
            <Button className="bg-red-600 hover:bg-red-700" onClick={cancel} disabled={busy} data-testid="confirm-cancel-button">{busy ? "Processando..." : "Confirmar cancelamento"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={emailOpen} onOpenChange={setEmailOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Enviar NF-e por e-mail</DialogTitle>
            <DialogDescription>Enviaremos a DANFE (PDF) e o XML da nota para o e-mail informado.</DialogDescription></DialogHeader>
          <div className="space-y-2 py-2">
            <Label>E-mail do destinatário</Label>
            <Input type="email" value={emailAddr} onChange={(e) => setEmailAddr(e.target.value)} data-testid="email-input" placeholder="cliente@empresa.com.br" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEmailOpen(false)}>Cancelar</Button>
            <Button onClick={enviarEmail} disabled={busy} data-testid="send-email-button">{busy ? "Enviando..." : "Enviar"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
