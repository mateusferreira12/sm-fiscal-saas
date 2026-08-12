import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { formatApiErrorDetail, money } from "@/lib/apiClient";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Check, Plus, Trash, ArrowLeft, ArrowRight, Users, Package } from "@phosphor-icons/react";
import { toast } from "sonner";

const steps = ["Destinatário", "Produtos", "Revisão"];

export default function InvoiceNew() {
  const [step, setStep] = useState(0);
  const [clients, setClients] = useState([]);
  const [products, setProducts] = useState([]);
  const [clienteId, setClienteId] = useState("");
  const [natureza, setNatureza] = useState("Venda de mercadoria");
  const [info, setInfo] = useState("");
  const [items, setItems] = useState([]);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/clients").then((r) => setClients(r.data));
    api.get("/products").then((r) => setProducts(r.data));
  }, []);

  const addItem = () => setItems([...items, { product_id: "", quantidade: 1, valor_unitario: 0 }]);
  const setItem = (idx, k, v) => setItems(items.map((it, i) => {
    if (i !== idx) return it;
    const next = { ...it, [k]: v };
    if (k === "product_id") {
      const p = products.find((x) => x.id === v);
      if (p) next.valor_unitario = p.valor;
    }
    return next;
  }));
  const removeItem = (idx) => setItems(items.filter((_, i) => i !== idx));

  const lineTotal = (it) => Number(it.quantidade || 0) * Number(it.valor_unitario || 0);
  const total = items.reduce((s, it) => s + lineTotal(it), 0);
  const cliente = clients.find((c) => c.id === clienteId);

  const canNext = step === 0 ? !!clienteId : step === 1 ? items.length > 0 && items.every((i) => i.product_id) : true;

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        natureza_operacao: natureza, cliente_id: clienteId, info_adicional: info,
        itens: items.map((it) => ({ product_id: it.product_id, quantidade: Number(it.quantidade), valor_unitario: Number(it.valor_unitario) })),
      };
      const { data } = await api.post("/invoices", payload);
      toast.success("Nota criada como rascunho");
      navigate(`/notas/${data.id}`);
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  return (
    <div>
      <PageHeader title="Nova Nota Fiscal" subtitle="Emissão de NF-e (modelo 55)" />
      <div className="p-8 max-w-4xl">
        <div className="flex items-center mb-8">
          {steps.map((s, i) => (
            <div key={s} className="flex items-center flex-1 last:flex-none">
              <div className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${i < step ? "bg-emerald-500 text-white" : i === step ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-500"}`}>
                  {i < step ? <Check size={16} weight="bold" /> : i + 1}
                </div>
                <span className={`text-sm font-medium ${i === step ? "text-slate-900" : "text-slate-400"}`}>{s}</span>
              </div>
              {i < steps.length - 1 && <div className={`flex-1 h-0.5 mx-3 ${i < step ? "bg-emerald-500" : "bg-slate-200"}`} />}
            </div>
          ))}
        </div>

        <Card className="p-8 border-slate-200">
          {step === 0 && (
            <div className="space-y-5">
              <div className="space-y-2">
                <Label>Natureza da operação</Label>
                <Input value={natureza} onChange={(e) => setNatureza(e.target.value)} data-testid="invoice-natureza-input" />
              </div>
              <div className="space-y-2">
                <Label>Cliente / Destinatário</Label>
                {clients.length === 0 ? (
                  <div className="text-sm text-slate-500 flex items-center gap-2 p-4 bg-slate-50 rounded-md">
                    <Users size={18} /> Nenhum cliente cadastrado. <button onClick={() => navigate("/clientes")} className="text-blue-600 underline">Cadastrar</button>
                  </div>
                ) : (
                  <Select value={clienteId} onValueChange={setClienteId}>
                    <SelectTrigger data-testid="invoice-cliente-select"><SelectValue placeholder="Selecione o cliente" /></SelectTrigger>
                    <SelectContent>{clients.map((c) => <SelectItem key={c.id} value={c.id}>{c.nome} — {c.cpf_cnpj}</SelectItem>)}</SelectContent>
                  </Select>
                )}
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              {products.length === 0 && (
                <div className="text-sm text-slate-500 flex items-center gap-2 p-4 bg-slate-50 rounded-md">
                  <Package size={18} /> Nenhum produto cadastrado. <button onClick={() => navigate("/produtos")} className="text-blue-600 underline">Cadastrar</button>
                </div>
              )}
              {items.map((it, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-3 items-end border-b border-slate-100 pb-4" data-testid={`item-row-${idx}`}>
                  <div className="col-span-5 space-y-2">
                    <Label className="text-xs">Produto</Label>
                    <Select value={it.product_id} onValueChange={(v) => setItem(idx, "product_id", v)}>
                      <SelectTrigger data-testid={`item-product-select-${idx}`}><SelectValue placeholder="Produto" /></SelectTrigger>
                      <SelectContent>{products.map((p) => <SelectItem key={p.id} value={p.id}>{p.codigo} — {p.descricao}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-2 space-y-2"><Label className="text-xs">Qtd</Label>
                    <Input type="number" step="0.01" value={it.quantidade} onChange={(e) => setItem(idx, "quantidade", e.target.value)} data-testid={`item-qty-${idx}`} /></div>
                  <div className="col-span-3 space-y-2"><Label className="text-xs">Valor Unit.</Label>
                    <Input type="number" step="0.01" value={it.valor_unitario} onChange={(e) => setItem(idx, "valor_unitario", e.target.value)} data-testid={`item-price-${idx}`} /></div>
                  <div className="col-span-1 text-sm font-medium pb-2">{money(lineTotal(it))}</div>
                  <div className="col-span-1"><button onClick={() => removeItem(idx)} className="text-slate-400 hover:text-red-600 p-2" data-testid={`remove-item-${idx}`}><Trash size={18} /></button></div>
                </div>
              ))}
              <Button variant="outline" onClick={addItem} disabled={products.length === 0} data-testid="add-item-button">
                <Plus size={18} className="mr-1" /> Adicionar item
              </Button>
              <div className="text-right text-lg font-bold text-slate-900 pt-2">Total: {money(total)}</div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-5">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-slate-500">Cliente:</span> <span className="font-medium">{cliente?.nome}</span></div>
                <div><span className="text-slate-500">Natureza:</span> <span className="font-medium">{natureza}</span></div>
              </div>
              <div className="border border-slate-200 rounded-md overflow-hidden">
                <table className="w-full text-sm">
                  <thead><tr className="bg-slate-50 text-left text-xs uppercase text-slate-500"><th className="px-4 py-2">Produto</th><th className="px-4 py-2">Qtd</th><th className="px-4 py-2">Unit.</th><th className="px-4 py-2 text-right">Total</th></tr></thead>
                  <tbody>
                    {items.map((it, i) => {
                      const p = products.find((x) => x.id === it.product_id);
                      return <tr key={i} className="border-t border-slate-100"><td className="px-4 py-2">{p?.descricao}</td><td className="px-4 py-2">{it.quantidade}</td><td className="px-4 py-2">{money(it.valor_unitario)}</td><td className="px-4 py-2 text-right">{money(lineTotal(it))}</td></tr>;
                    })}
                  </tbody>
                </table>
              </div>
              <div className="space-y-2"><Label>Informações adicionais</Label>
                <Textarea value={info} onChange={(e) => setInfo(e.target.value)} rows={3} data-testid="invoice-info-input" /></div>
              <div className="text-right text-2xl font-bold text-slate-900">Total: {money(total)}</div>
            </div>
          )}

          <div className="flex justify-between mt-8 pt-6 border-t border-slate-100">
            <Button variant="outline" onClick={() => step === 0 ? navigate("/notas") : setStep(step - 1)} data-testid="wizard-back-button">
              <ArrowLeft size={18} className="mr-1" /> {step === 0 ? "Cancelar" : "Voltar"}
            </Button>
            {step < 2 ? (
              <Button onClick={() => setStep(step + 1)} disabled={!canNext} data-testid="wizard-next-button">Próximo <ArrowRight size={18} className="ml-1" /></Button>
            ) : (
              <Button onClick={save} disabled={saving} data-testid="wizard-save-button">{saving ? "Salvando..." : "Criar Nota"}</Button>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
