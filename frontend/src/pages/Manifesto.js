import { useEffect, useState } from "react";
import api, { formatApiErrorDetail } from "@/lib/apiClient";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SealCheck, Warning } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Manifesto() {
  const [tipos, setTipos] = useState({});
  const [list, setList] = useState([]);
  const [chave, setChave] = useState("");
  const [tipo, setTipo] = useState("210210");
  const [just, setJust] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/manifestacoes").then((r) => setList(r.data));
  useEffect(() => {
    api.get("/manifestacoes/tipos").then((r) => setTipos(r.data));
    load();
  }, []);

  const precisaJust = tipo === "210220" || tipo === "210240";

  const submit = async () => {
    const ch = chave.replace(/\D/g, "");
    if (ch.length !== 44) return toast.error("A chave de acesso deve ter 44 dígitos");
    if (precisaJust && just.trim().length < 15) return toast.error("Justificativa mínima de 15 caracteres");
    setBusy(true);
    try {
      const { data } = await api.post("/manifestacoes", { chave: ch, tipo, justificativa: just.trim() });
      setChave(""); setJust(""); load();
      if (data.status === "registrado") toast.success("Manifestação registrada no SEFAZ");
      else toast.error(data.motivo || "Manifestação não registrada");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader title="Manifestação do Destinatário" subtitle="Ciência, confirmação ou desconhecimento de NF-e recebidas" />
      <div className="p-8 max-w-4xl space-y-6">
        <Card className="p-8 border-slate-200 space-y-5">
          <div className="space-y-2">
            <Label>Chave de acesso da NF-e (44 dígitos)</Label>
            <Input value={chave} onChange={(e) => setChave(e.target.value)} data-testid="manifesto-chave-input" placeholder="Chave da nota recebida" className="mono" />
          </div>
          <div className="space-y-2">
            <Label>Tipo de manifestação</Label>
            <Select value={tipo} onValueChange={setTipo}>
              <SelectTrigger data-testid="manifesto-tipo-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(tipos).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {precisaJust && (
            <div className="space-y-2">
              <Label>Justificativa (mín. 15 caracteres)</Label>
              <Textarea rows={3} value={just} onChange={(e) => setJust(e.target.value)} data-testid="manifesto-just-input" />
            </div>
          )}
          <Button onClick={submit} disabled={busy} data-testid="manifesto-submit-button">
            <SealCheck size={18} className="mr-1" /> {busy ? "Enviando..." : "Registrar manifestação"}
          </Button>
        </Card>

        <Card className="border-slate-200">
          <div className="p-6 border-b border-slate-200"><h3 className="text-sm font-semibold text-slate-800">Manifestações registradas</h3></div>
          {list.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">
              <Warning size={32} className="mx-auto text-slate-300 mb-2" weight="duotone" /> Nenhuma manifestação ainda
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-100">
                <th className="px-6 py-3">Chave</th><th className="px-6 py-3">Tipo</th><th className="px-6 py-3">Status</th><th className="px-6 py-3">Protocolo</th>
              </tr></thead>
              <tbody>
                {list.map((m) => (
                  <tr key={m.id} className="border-b border-slate-50" data-testid={`manifesto-row-${m.id}`}>
                    <td className="px-6 py-3 mono text-xs">{m.chave.slice(0, 20)}...</td>
                    <td className="px-6 py-3">{m.descricao}</td>
                    <td className="px-6 py-3"><span className={`text-xs font-medium ${m.status === "registrado" ? "text-emerald-700" : "text-red-700"}`}>{m.motivo}</span></td>
                    <td className="px-6 py-3 mono text-xs text-slate-500">{m.protocolo || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}
