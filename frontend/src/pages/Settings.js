import { useEffect, useRef, useState } from "react";
import api, { formatApiErrorDetail } from "@/lib/apiClient";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ShieldCheck, SealCheck, Warning, Image as ImageIcon } from "@phosphor-icons/react";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";

const UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"];

export default function Settings() {
  const [c, setC] = useState(null);
  const [certPass, setCertPass] = useState("");
  const fileRef = useRef(null);
  const logoRef = useRef(null);

  const load = () => api.get("/company").then((r) => setC(r.data));
  useEffect(() => { load(); }, []);
  if (!c) return <div className="p-8 text-slate-400">Carregando...</div>;

  const set = (k, v) => setC({ ...c, [k]: v });
  const setEnd = (k, v) => setC({ ...c, endereco: { ...c.endereco, [k]: v } });
  const setSef = (k, v) => setC({ ...c, sefaz: { ...c.sefaz, [k]: v } });

  const save = async () => {
    try {
      const payload = {
        razao_social: c.razao_social, nome_fantasia: c.nome_fantasia, cnpj: c.cnpj,
        ie: c.ie, im: c.im, crt: Number(c.crt), endereco: c.endereco, sefaz: c.sefaz,
        proxima_serie: Number(c.proxima_serie), proximo_numero: Number(c.proximo_numero),
      };
      await api.put("/company", payload);
      toast.success("Configurações salvas");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  const uploadCert = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return toast.error("Selecione o arquivo .pfx");
    if (!certPass) return toast.error("Informe a senha do certificado");
    const fd = new FormData();
    fd.append("file", file); fd.append("senha", certPass);
    try {
      const { data } = await api.post("/company/certificate", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setC(data); setCertPass(""); toast.success("Certificado instalado");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  const uploadLogo = async () => {
    const file = logoRef.current?.files?.[0];
    if (!file) return toast.error("Selecione uma imagem");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/company/logo", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setC(data); toast.success("Logo enviada");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader title="Configurações" subtitle="Dados do emitente, SEFAZ e certificado">
        <Button onClick={save} data-testid="save-settings-button">Salvar</Button>
      </PageHeader>
      <div className="p-8 max-w-4xl">
        <Tabs defaultValue="empresa">
          <TabsList data-testid="settings-tabs">
            <TabsTrigger value="empresa" data-testid="tab-empresa">Empresa</TabsTrigger>
            <TabsTrigger value="fiscal" data-testid="tab-fiscal">Fiscal / SEFAZ</TabsTrigger>
            <TabsTrigger value="certificado" data-testid="tab-certificado">Certificado</TabsTrigger>
          </TabsList>

          <TabsContent value="empresa">
            <Card className="p-8 border-slate-200 grid grid-cols-2 gap-5">
              <div className="space-y-2 col-span-2"><Label>Razão Social</Label><Input value={c.razao_social} onChange={(e) => set("razao_social", e.target.value)} data-testid="razao-input" /></div>
              <div className="space-y-2"><Label>Nome Fantasia</Label><Input value={c.nome_fantasia} onChange={(e) => set("nome_fantasia", e.target.value)} /></div>
              <div className="space-y-2"><Label>CNPJ</Label><Input value={c.cnpj} onChange={(e) => set("cnpj", e.target.value)} data-testid="cnpj-input" /></div>
              <div className="space-y-2"><Label>Inscrição Estadual</Label><Input value={c.ie} onChange={(e) => set("ie", e.target.value)} /></div>
              <div className="space-y-2"><Label>Inscrição Municipal</Label><Input value={c.im} onChange={(e) => set("im", e.target.value)} /></div>
              <div className="space-y-2 col-span-2"><Label>Regime Tributário</Label>
                <Select value={String(c.crt)} onValueChange={(v) => set("crt", v)}>
                  <SelectTrigger data-testid="crt-select"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="1">Simples Nacional</SelectItem><SelectItem value="2">Simples Nacional - excesso</SelectItem><SelectItem value="3">Regime Normal</SelectItem></SelectContent>
                </Select></div>
              <div className="col-span-2 text-xs font-semibold uppercase tracking-wider text-slate-500 pt-2">Endereço</div>
              <div className="space-y-2 col-span-2"><Label>Logradouro</Label><Input value={c.endereco.logradouro} onChange={(e) => setEnd("logradouro", e.target.value)} /></div>
              <div className="space-y-2"><Label>Número</Label><Input value={c.endereco.numero} onChange={(e) => setEnd("numero", e.target.value)} /></div>
              <div className="space-y-2"><Label>Bairro</Label><Input value={c.endereco.bairro} onChange={(e) => setEnd("bairro", e.target.value)} /></div>
              <div className="space-y-2"><Label>Município</Label><Input value={c.endereco.municipio} onChange={(e) => setEnd("municipio", e.target.value)} /></div>
              <div className="space-y-2"><Label>Cód. Município (IBGE)</Label><Input value={c.endereco.cod_municipio} onChange={(e) => setEnd("cod_municipio", e.target.value)} /></div>
              <div className="space-y-2"><Label>UF</Label><Input maxLength={2} value={c.endereco.uf} onChange={(e) => setEnd("uf", e.target.value.toUpperCase())} /></div>
              <div className="space-y-2"><Label>CEP</Label><Input value={c.endereco.cep} onChange={(e) => setEnd("cep", e.target.value)} /></div>
              <div className="col-span-2 text-xs font-semibold uppercase tracking-wider text-slate-500 pt-2 flex items-center gap-1"><ImageIcon size={14} /> Logomarca (aparece na DANFE)</div>
              <div className="space-y-2"><Label>Arquivo (PNG/JPG)</Label><Input type="file" accept="image/*" ref={logoRef} data-testid="logo-file-input" /></div>
              <div className="space-y-2 flex items-end gap-3">
                <Button type="button" variant="outline" onClick={uploadLogo} data-testid="upload-logo-button">Enviar logo</Button>
                {c.logo_filename && <span className="text-xs text-emerald-600 pb-2">{c.logo_filename}</span>}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="fiscal">
            <Card className="p-8 border-slate-200 grid grid-cols-2 gap-5">
              <div className="space-y-2"><Label>UF de emissão (SEFAZ)</Label>
                <Select value={c.sefaz.uf} onValueChange={(v) => setSef("uf", v)}>
                  <SelectTrigger data-testid="sefaz-uf-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{UFS.map((u) => <SelectItem key={u} value={u}>{u}</SelectItem>)}</SelectContent>
                </Select></div>
              <div className="space-y-2"><Label>Ambiente</Label>
                <Select value={String(c.sefaz.ambiente)} onValueChange={(v) => setSef("ambiente", Number(v))}>
                  <SelectTrigger data-testid="sefaz-amb-select"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="2">Homologação (testes)</SelectItem><SelectItem value="1">Produção</SelectItem></SelectContent>
                </Select></div>
              <div className="space-y-2"><Label>Série da NF-e</Label><Input type="number" value={c.proxima_serie} onChange={(e) => set("proxima_serie", e.target.value)} data-testid="serie-input" /></div>
              <div className="space-y-2"><Label>Próximo número</Label><Input type="number" value={c.proximo_numero} onChange={(e) => set("proximo_numero", e.target.value)} data-testid="numero-input" /></div>
              <div className="space-y-2"><Label>CSC (Token)</Label><Input value={c.sefaz.csc} onChange={(e) => setSef("csc", e.target.value)} /></div>
              <div className="space-y-2"><Label>ID do CSC</Label><Input value={c.sefaz.csc_id} onChange={(e) => setSef("csc_id", e.target.value)} /></div>
              <div className="col-span-2 flex items-center justify-between rounded-md border border-slate-200 p-4">
                <div>
                  <div className="text-sm font-medium text-slate-800">Contingência automática (SVC)</div>
                  <div className="text-xs text-slate-500">Emite via SVC-RS/SVC-AN quando o SEFAZ da UF estiver indisponível.</div>
                </div>
                <Switch checked={c.sefaz.contingencia !== false} onCheckedChange={(v) => setSef("contingencia", v)} data-testid="contingencia-switch" />
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="certificado">
            <Card className="p-8 border-slate-200 space-y-6">
              {c.certificate?.installed ? (
                <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-100 rounded-md p-4">
                  <SealCheck size={24} className="text-emerald-600" weight="fill" />
                  <div className="text-sm">
                    <div className="font-medium text-slate-800">Certificado instalado: {c.certificate.filename}</div>
                    <div className="text-slate-500">Válido até: {c.certificate.valid_until ? new Date(c.certificate.valid_until).toLocaleDateString("pt-BR") : "—"}</div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-3 bg-amber-50 border border-amber-100 rounded-md p-4">
                  <Warning size={24} className="text-amber-600" weight="fill" />
                  <div className="text-sm text-slate-700">Nenhum certificado A1 instalado. Necessário para assinar e transmitir a NF-e ao SEFAZ.</div>
                </div>
              )}
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-800"><ShieldCheck size={20} className="text-blue-600" /> Certificado Digital A1 (.pfx / .p12)</div>
              <div className="grid grid-cols-2 gap-5">
                <div className="space-y-2"><Label>Arquivo do certificado</Label>
                  <Input type="file" accept=".pfx,.p12" ref={fileRef} data-testid="cert-file-input" /></div>
                <div className="space-y-2"><Label>Senha do certificado</Label>
                  <Input type="password" value={certPass} onChange={(e) => setCertPass(e.target.value)} data-testid="cert-pass-input" /></div>
              </div>
              <Button onClick={uploadCert} data-testid="upload-cert-button">Instalar certificado</Button>
              <p className="text-xs text-slate-500">O certificado é validado e armazenado com segurança para assinar suas notas. A transmissão real ao SEFAZ requer um certificado ICP-Brasil válido.</p>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
