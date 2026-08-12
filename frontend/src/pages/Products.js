import { useEffect, useState } from "react";
import api, { formatApiErrorDetail, money } from "@/lib/apiClient";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Plus, PencilSimple, Trash, Package } from "@phosphor-icons/react";
import { toast } from "sonner";

const empty = {
  codigo: "", descricao: "", ncm: "00000000", cfop: "5102", unidade: "UN", valor: 0, origem: "0",
  cst_icms: "102", icms_aliquota: 0, ipi_aliquota: 0, pis_aliquota: 0.65, cofins_aliquota: 3,
};

export default function Products() {
  const [products, setProducts] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editId, setEditId] = useState(null);

  const load = () => api.get("/products").then((r) => setProducts(r.data));
  useEffect(() => { load(); }, []);

  const openNew = () => { setForm(empty); setEditId(null); setOpen(true); };
  const openEdit = (p) => { setForm({ ...empty, ...p }); setEditId(p.id); setOpen(true); };

  const num = (k, v) => setForm((f) => ({ ...f, [k]: v === "" ? 0 : Number(v) }));

  const save = async () => {
    if (!form.codigo || !form.descricao) return toast.error("Informe código e descrição");
    const payload = { ...form };
    ["id", "user_id", "created_at"].forEach((k) => delete payload[k]);
    ["valor", "icms_aliquota", "ipi_aliquota", "pis_aliquota", "cofins_aliquota"].forEach((k) => (payload[k] = Number(payload[k])));
    try {
      if (editId) await api.put(`/products/${editId}`, payload);
      else await api.post("/products", payload);
      toast.success("Produto salvo"); setOpen(false); load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Excluir este produto?")) return;
    await api.delete(`/products/${id}`); toast.success("Produto excluído"); load();
  };

  return (
    <div>
      <PageHeader title="Produtos" subtitle="Itens e configuração tributária">
        <Button onClick={openNew} data-testid="new-product-button"><Plus size={18} weight="bold" className="mr-1" /> Novo Produto</Button>
      </PageHeader>
      <div className="p-8">
        <Card className="border-slate-200">
          {products.length === 0 ? (
            <div className="p-12 text-center">
              <Package size={40} className="mx-auto text-slate-300 mb-3" weight="duotone" />
              <p className="text-slate-500 text-sm">Nenhum produto cadastrado</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200">
                <th className="px-6 py-3">Código</th><th className="px-6 py-3">Descrição</th><th className="px-6 py-3">NCM</th>
                <th className="px-6 py-3">CFOP</th><th className="px-6 py-3">Valor</th><th className="px-6 py-3 text-right">Ações</th>
              </tr></thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors" data-testid={`product-row-${p.id}`}>
                    <td className="px-6 py-3 font-medium mono">{p.codigo}</td>
                    <td className="px-6 py-3">{p.descricao}</td>
                    <td className="px-6 py-3 text-slate-600 mono">{p.ncm}</td>
                    <td className="px-6 py-3 text-slate-600 mono">{p.cfop}</td>
                    <td className="px-6 py-3">{money(p.valor)}</td>
                    <td className="px-6 py-3 text-right">
                      <button onClick={() => openEdit(p)} className="text-slate-400 hover:text-blue-600 p-1.5" data-testid={`edit-product-${p.id}`}><PencilSimple size={18} /></button>
                      <button onClick={() => remove(p.id)} className="text-slate-400 hover:text-red-600 p-1.5" data-testid={`delete-product-${p.id}`}><Trash size={18} /></button>
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
          <DialogHeader><DialogTitle>{editId ? "Editar" : "Novo"} Produto</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-4 py-2">
            <div className="space-y-2"><Label>Código</Label><Input value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} data-testid="product-codigo-input" /></div>
            <div className="space-y-2"><Label>Unidade</Label><Input value={form.unidade} onChange={(e) => setForm({ ...form, unidade: e.target.value })} data-testid="product-unidade-input" /></div>
            <div className="space-y-2 col-span-2"><Label>Descrição</Label><Input value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} data-testid="product-descricao-input" /></div>
            <div className="space-y-2"><Label>NCM</Label><Input value={form.ncm} onChange={(e) => setForm({ ...form, ncm: e.target.value })} data-testid="product-ncm-input" /></div>
            <div className="space-y-2"><Label>CFOP</Label><Input value={form.cfop} onChange={(e) => setForm({ ...form, cfop: e.target.value })} data-testid="product-cfop-input" /></div>
            <div className="space-y-2"><Label>Valor unitário (R$)</Label><Input type="number" step="0.01" value={form.valor} onChange={(e) => num("valor", e.target.value)} data-testid="product-valor-input" /></div>
            <div className="space-y-2"><Label>CST/CSOSN ICMS</Label><Input value={form.cst_icms} onChange={(e) => setForm({ ...form, cst_icms: e.target.value })} data-testid="product-cst-input" /></div>
            <div className="col-span-2 text-xs font-semibold uppercase tracking-wider text-slate-500 pt-2">Alíquotas (%)</div>
            <div className="space-y-2"><Label>ICMS</Label><Input type="number" step="0.01" value={form.icms_aliquota} onChange={(e) => num("icms_aliquota", e.target.value)} data-testid="product-icms-input" /></div>
            <div className="space-y-2"><Label>IPI</Label><Input type="number" step="0.01" value={form.ipi_aliquota} onChange={(e) => num("ipi_aliquota", e.target.value)} data-testid="product-ipi-input" /></div>
            <div className="space-y-2"><Label>PIS</Label><Input type="number" step="0.01" value={form.pis_aliquota} onChange={(e) => num("pis_aliquota", e.target.value)} data-testid="product-pis-input" /></div>
            <div className="space-y-2"><Label>COFINS</Label><Input type="number" step="0.01" value={form.cofins_aliquota} onChange={(e) => num("cofins_aliquota", e.target.value)} data-testid="product-cofins-input" /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-product-button">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
