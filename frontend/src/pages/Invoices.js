import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { money, formatApiErrorDetail } from "@/lib/apiClient";
import { PageHeader, StatusBadge } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Receipt, MagnifyingGlass, Prohibit } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [q, setQ] = useState("");
  const [inutOpen, setInutOpen] = useState(false);
  const [inutList, setInutList] = useState([]);
  const [form, setForm] = useState({ serie: 1, numero_inicial: "", numero_final: "", justificativa: "" });
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const loadInut = () => api.get("/inutilizacoes").then((r) => setInutList(r.data));
  useEffect(() => { api.get("/invoices").then((r) => setInvoices(r.data)); loadInut(); }, []);

  const filtered = invoices.filter((i) =>
    i.cliente?.nome?.toLowerCase().includes(q.toLowerCase()) || String(i.numero).includes(q));

  const submitInut = async () => {
    if (!form.numero_inicial || !form.numero_final) return toast.error("Informe a faixa de numeração");
    if (form.justificativa.trim().length < 15) return toast.error("A justificativa deve ter ao menos 15 caracteres");
    setBusy(true);
    try {
      const payload = {
        serie: Number(form.serie), numero_inicial: Number(form.numero_inicial),
        numero_final: Number(form.numero_final), justificativa: form.justificativa.trim(),
      };
      const { data } = await api.post("/inutilizacoes", payload);
      setInutOpen(false);
      setForm({ serie: 1, numero_inicial: "", numero_final: "", justificativa: "" });
      loadInut();
      if (data.status === "inutilizada") toast.success("Numeração inutilizada no SEFAZ");
      else toast.error(data.motivo || "Inutilização não concluída");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader title="Notas Fiscais" subtitle="Emissão e acompanhamento de NF-e">
        <Button variant="outline" onClick={() => setInutOpen(true)} data-testid="inutilizar-button">
          <Prohibit size={18} className="mr-1" /> Inutilizar Numeração
        </Button>
        <Button onClick={() => navigate("/notas/nova")} data-testid="new-invoice-button">
          <Plus size={18} weight="bold" className="mr-1" /> Nova Nota
        </Button>
      </PageHeader>
      <div className="p-8 space-y-4">
        <div className="relative max-w-sm">
          <MagnifyingGlass size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input placeholder="Buscar por cliente ou número..." value={q} onChange={(e) => setQ(e.target.value)} className="pl-9" data-testid="invoice-search-input" />
        </div>
        <Card className="border-slate-200">
          {filtered.length === 0 ? (
            <div className="p-12 text-center">
              <Receipt size={40} className="mx-auto text-slate-300 mb-3" weight="duotone" />
              <p className="text-slate-500 text-sm">Nenhuma nota encontrada</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200">
                <th className="px-6 py-3">Número</th><th className="px-6 py-3">Série</th><th className="px-6 py-3">Cliente</th>
                <th className="px-6 py-3">Valor</th><th className="px-6 py-3">Status</th><th className="px-6 py-3">Chave</th>
              </tr></thead>
              <tbody>
                {filtered.map((i) => (
                  <tr key={i.id} onClick={() => navigate(`/notas/${i.id}`)} className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors" data-testid={`invoice-row-${i.id}`}>
                    <td className="px-6 py-3 font-medium">#{String(i.numero).padStart(3, "0")}</td>
                    <td className="px-6 py-3 text-slate-600">{i.serie}</td>
                    <td className="px-6 py-3 text-slate-600">{i.cliente?.nome}</td>
                    <td className="px-6 py-3">{money(i.totais?.v_nf)}</td>
                    <td className="px-6 py-3"><StatusBadge status={i.status} /></td>
                    <td className="px-6 py-3 text-slate-400 mono text-xs">{i.chave_acesso ? `${i.chave_acesso.slice(0, 12)}...` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {inutList.length > 0 && (
          <Card className="border-slate-200" data-testid="inutilizacoes-card">
            <div className="p-6 border-b border-slate-200"><h3 className="text-sm font-semibold text-slate-800">Numerações inutilizadas</h3></div>
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-100">
                <th className="px-6 py-3">Série</th><th className="px-6 py-3">Faixa</th><th className="px-6 py-3">Justificativa</th>
                <th className="px-6 py-3">Status</th><th className="px-6 py-3">Protocolo</th>
              </tr></thead>
              <tbody>
                {inutList.map((u) => (
                  <tr key={u.id} className="border-b border-slate-50" data-testid={`inut-row-${u.id}`}>
                    <td className="px-6 py-3">{u.serie}</td>
                    <td className="px-6 py-3 mono">{u.numero_inicial} – {u.numero_final}</td>
                    <td className="px-6 py-3 text-slate-600 max-w-xs truncate">{u.justificativa}</td>
                    <td className="px-6 py-3"><span className={`text-xs font-medium ${u.status === "inutilizada" ? "text-emerald-700" : "text-red-700"}`}>{u.motivo}</span></td>
                    <td className="px-6 py-3 mono text-xs text-slate-500">{u.protocolo || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </div>

      <Dialog open={inutOpen} onOpenChange={setInutOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Inutilizar Numeração</DialogTitle>
            <DialogDescription>Inutilize uma faixa de números de NF-e não utilizados junto ao SEFAZ. Requer certificado A1.</DialogDescription></DialogHeader>
          <div className="grid grid-cols-3 gap-4 py-2">
            <div className="space-y-2"><Label>Série</Label><Input type="number" value={form.serie} onChange={(e) => setForm({ ...form, serie: e.target.value })} data-testid="inut-serie-input" /></div>
            <div className="space-y-2"><Label>Nº Inicial</Label><Input type="number" value={form.numero_inicial} onChange={(e) => setForm({ ...form, numero_inicial: e.target.value })} data-testid="inut-ini-input" /></div>
            <div className="space-y-2"><Label>Nº Final</Label><Input type="number" value={form.numero_final} onChange={(e) => setForm({ ...form, numero_final: e.target.value })} data-testid="inut-fim-input" /></div>
            <div className="space-y-2 col-span-3"><Label>Justificativa (mín. 15 caracteres)</Label>
              <Textarea rows={3} value={form.justificativa} onChange={(e) => setForm({ ...form, justificativa: e.target.value })} data-testid="inut-just-input" placeholder="Motivo da inutilização..." /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setInutOpen(false)}>Cancelar</Button>
            <Button onClick={submitInut} disabled={busy} data-testid="submit-inut-button">{busy ? "Enviando..." : "Inutilizar"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
