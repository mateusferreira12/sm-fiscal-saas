import { useEffect, useState } from "react";
import api, { formatApiErrorDetail } from "@/lib/apiClient";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, PencilSimple, Trash, Users } from "@phosphor-icons/react";
import { toast } from "sonner";

const emptyEndereco = { logradouro: "", numero: "", bairro: "", municipio: "", cod_municipio: "", uf: "", cep: "" };
const emptyClient = { tipo: "PJ", nome: "", cpf_cnpj: "", ie: "", email: "", fone: "", indicador_ie: 9, endereco: { ...emptyEndereco } };

export default function Clients() {
  const [clients, setClients] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyClient);
  const [editId, setEditId] = useState(null);

  const load = () => api.get("/clients").then((r) => setClients(r.data));
  useEffect(() => { load(); }, []);

  const openNew = () => { setForm({ ...emptyClient, endereco: { ...emptyEndereco } }); setEditId(null); setOpen(true); };
  const openEdit = (c) => { setForm({ ...emptyClient, ...c, endereco: { ...emptyEndereco, ...c.endereco } }); setEditId(c.id); setOpen(true); };

  const save = async () => {
    if (!form.nome) return toast.error("Informe o nome");
    const payload = { ...form };
    delete payload.id; delete payload.user_id; delete payload.created_at;
    payload.indicador_ie = Number(payload.indicador_ie);
    try {
      if (editId) await api.put(`/clients/${editId}`, payload);
      else await api.post("/clients", payload);
      toast.success("Cliente salvo");
      setOpen(false); load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Excluir este cliente?")) return;
    await api.delete(`/clients/${id}`); toast.success("Cliente excluído"); load();
  };

  const setEnd = (k, v) => setForm((f) => ({ ...f, endereco: { ...f.endereco, [k]: v } }));

  return (
    <div>
      <PageHeader title="Clientes" subtitle="Destinatários das notas fiscais">
        <Button onClick={openNew} data-testid="new-client-button"><Plus size={18} weight="bold" className="mr-1" /> Novo Cliente</Button>
      </PageHeader>
      <div className="p-8">
        <Card className="border-slate-200">
          {clients.length === 0 ? (
            <div className="p-12 text-center">
              <Users size={40} className="mx-auto text-slate-300 mb-3" weight="duotone" />
              <p className="text-slate-500 text-sm">Nenhum cliente cadastrado</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200">
                <th className="px-6 py-3">Nome</th><th className="px-6 py-3">Documento</th>
                <th className="px-6 py-3">Cidade</th><th className="px-6 py-3">E-mail</th><th className="px-6 py-3 text-right">Ações</th>
              </tr></thead>
              <tbody>
                {clients.map((c) => (
                  <tr key={c.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors" data-testid={`client-row-${c.id}`}>
                    <td className="px-6 py-3 font-medium">{c.nome}</td>
                    <td className="px-6 py-3 text-slate-600 mono">{c.cpf_cnpj}</td>
                    <td className="px-6 py-3 text-slate-600">{c.endereco?.municipio} {c.endereco?.uf && `- ${c.endereco.uf}`}</td>
                    <td className="px-6 py-3 text-slate-600">{c.email}</td>
                    <td className="px-6 py-3 text-right">
                      <button onClick={() => openEdit(c)} className="text-slate-400 hover:text-blue-600 p-1.5" data-testid={`edit-client-${c.id}`}><PencilSimple size={18} /></button>
                      <button onClick={() => remove(c.id)} className="text-slate-400 hover:text-red-600 p-1.5" data-testid={`delete-client-${c.id}`}><Trash size={18} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editId ? "Editar" : "Novo"} Cliente</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-4 py-2">
            <div className="space-y-2">
              <Label>Tipo</Label>
              <Select value={form.tipo} onValueChange={(v) => setForm({ ...form, tipo: v })}>
                <SelectTrigger data-testid="client-tipo-select"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="PJ">Pessoa Jurídica</SelectItem><SelectItem value="PF">Pessoa Física</SelectItem></SelectContent>
              </Select>
            </div>
            <div className="space-y-2"><Label>{form.tipo === "PJ" ? "CNPJ" : "CPF"}</Label>
              <Input value={form.cpf_cnpj} onChange={(e) => setForm({ ...form, cpf_cnpj: e.target.value })} data-testid="client-doc-input" /></div>
            <div className="space-y-2 col-span-2"><Label>Nome / Razão Social</Label>
              <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} data-testid="client-nome-input" /></div>
            <div className="space-y-2"><Label>Inscrição Estadual</Label>
              <Input value={form.ie} onChange={(e) => setForm({ ...form, ie: e.target.value })} data-testid="client-ie-input" /></div>
            <div className="space-y-2"><Label>Indicador IE</Label>
              <Select value={String(form.indicador_ie)} onValueChange={(v) => setForm({ ...form, indicador_ie: v })}>
                <SelectTrigger data-testid="client-indie-select"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="1">Contribuinte</SelectItem><SelectItem value="2">Isento</SelectItem><SelectItem value="9">Não contribuinte</SelectItem></SelectContent>
              </Select></div>
            <div className="space-y-2"><Label>E-mail</Label>
              <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="client-email-input" /></div>
            <div className="space-y-2"><Label>Telefone</Label>
              <Input value={form.fone} onChange={(e) => setForm({ ...form, fone: e.target.value })} data-testid="client-fone-input" /></div>
            <div className="col-span-2 text-xs font-semibold uppercase tracking-wider text-slate-500 pt-2">Endereço</div>
            <div className="space-y-2 col-span-2"><Label>Logradouro</Label>
              <Input value={form.endereco.logradouro} onChange={(e) => setEnd("logradouro", e.target.value)} /></div>
            <div className="space-y-2"><Label>Número</Label><Input value={form.endereco.numero} onChange={(e) => setEnd("numero", e.target.value)} /></div>
            <div className="space-y-2"><Label>Bairro</Label><Input value={form.endereco.bairro} onChange={(e) => setEnd("bairro", e.target.value)} /></div>
            <div className="space-y-2"><Label>Município</Label><Input value={form.endereco.municipio} onChange={(e) => setEnd("municipio", e.target.value)} /></div>
            <div className="space-y-2"><Label>Cód. Município (IBGE)</Label><Input value={form.endereco.cod_municipio} onChange={(e) => setEnd("cod_municipio", e.target.value)} /></div>
            <div className="space-y-2"><Label>UF</Label><Input maxLength={2} value={form.endereco.uf} onChange={(e) => setEnd("uf", e.target.value.toUpperCase())} /></div>
            <div className="space-y-2"><Label>CEP</Label><Input value={form.endereco.cep} onChange={(e) => setEnd("cep", e.target.value)} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-client-button">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
