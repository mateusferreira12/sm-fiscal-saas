import { useEffect, useState } from "react";
import api, { money, downloadFile } from "@/lib/apiClient";
import { PageHeader, StatusBadge } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DownloadSimple, ChartBar, FilePdf } from "@phosphor-icons/react";

export default function Reports() {
  const today = new Date().toISOString().slice(0, 10);
  const first = today.slice(0, 8) + "01";
  const [start, setStart] = useState(first);
  const [end, setEnd] = useState(today);
  const [data, setData] = useState(null);

  const load = () => api.get(`/reports?start=${start}&end=${end}`).then((r) => setData(r.data));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const t = data?.totais || {};

  return (
    <div>
      <PageHeader title="Relatórios Fiscais" subtitle="Totais de impostos por período">
        <Button variant="outline" onClick={() => downloadFile(`/reports/export.pdf?start=${start}&end=${end}`, "relatorio-nfe.pdf", true)} data-testid="export-pdf-button">
          <FilePdf size={18} className="mr-1" /> Exportar PDF
        </Button>
        <Button variant="outline" onClick={() => downloadFile(`/reports/export.csv?start=${start}&end=${end}`, "relatorio-nfe.csv")} data-testid="export-csv-button">
          <DownloadSimple size={18} className="mr-1" /> Exportar CSV
        </Button>
      </PageHeader>
      <div className="p-8 space-y-6">
        <Card className="p-6 border-slate-200 flex flex-wrap items-end gap-4">
          <div className="space-y-2"><Label>De</Label><Input type="date" value={start} onChange={(e) => setStart(e.target.value)} data-testid="report-start-input" /></div>
          <div className="space-y-2"><Label>Até</Label><Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} data-testid="report-end-input" /></div>
          <Button onClick={load} data-testid="apply-filter-button">Aplicar</Button>
        </Card>

        {data && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {[["Notas", data.count, false], ["Faturadas", data.faturadas, false],
                ["Produtos", t.v_prod, true], ["ICMS", t.v_icms, true],
                ["IPI", t.v_ipi, true], ["PIS+COFINS", (t.v_pis || 0) + (t.v_cofins || 0), true]].map(([l, v, m], i) => (
                <Card key={i} className="p-5 border-slate-200">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">{l}</div>
                  <div className="text-xl font-bold text-slate-900 mt-2">{m ? money(v) : v}</div>
                </Card>
              ))}
            </div>
            <Card className="p-6 border-slate-200 flex items-center justify-between bg-blue-50 border-blue-100">
              <div className="flex items-center gap-2 text-slate-700"><ChartBar size={22} className="text-blue-600" weight="duotone" /> Faturamento total no período</div>
              <div className="text-2xl font-bold text-blue-600">{money(t.v_nf)}</div>
            </Card>

            <Card className="border-slate-200">
              <div className="p-6 border-b border-slate-200"><h3 className="text-sm font-semibold text-slate-800">Notas do período</h3></div>
              {data.notas.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-sm">Nenhuma nota no período</div>
              ) : (
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-100">
                    <th className="px-6 py-3">Número</th><th className="px-6 py-3">Data</th><th className="px-6 py-3">Cliente</th>
                    <th className="px-6 py-3">Impostos</th><th className="px-6 py-3">Total</th><th className="px-6 py-3">Status</th>
                  </tr></thead>
                  <tbody>
                    {data.notas.map((n) => {
                      const nt = n.totais || {};
                      const imp = (nt.v_icms || 0) + (nt.v_ipi || 0) + (nt.v_pis || 0) + (nt.v_cofins || 0);
                      return (
                        <tr key={n.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors" data-testid={`report-row-${n.id}`}>
                          <td className="px-6 py-3 font-medium">#{String(n.numero).padStart(3, "0")}</td>
                          <td className="px-6 py-3 text-slate-600">{(n.data_emissao || "").slice(0, 10)}</td>
                          <td className="px-6 py-3 text-slate-600">{n.cliente?.nome}</td>
                          <td className="px-6 py-3">{money(imp)}</td>
                          <td className="px-6 py-3 font-medium">{money(nt.v_nf)}</td>
                          <td className="px-6 py-3"><StatusBadge status={n.status} /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
