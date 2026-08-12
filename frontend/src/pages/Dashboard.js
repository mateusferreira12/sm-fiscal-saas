import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { money } from "@/lib/apiClient";
import { PageHeader, StatusBadge } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import { Receipt, CurrencyDollar, Percent, Users, Plus } from "@phosphor-icons/react";

const STATUS_COLORS = { autorizada: "#10B981", pendente: "#F59E0B", rascunho: "#94A3B8", rejeitada: "#EF4444", cancelada: "#DC2626" };

function StatCard({ icon: Icon, label, value, tint, delay }) {
  return (
    <Card className="p-6 border-slate-200 animate-fade-in-up" style={{ animationDelay: `${delay}ms` }} data-testid={`stat-${label}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</span>
        <span className={`w-9 h-9 rounded-md flex items-center justify-center ${tint}`}><Icon size={20} weight="duotone" /></span>
      </div>
      <div className="text-2xl font-bold text-slate-900 mt-3 tracking-tight">{value}</div>
    </Card>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => { api.get("/dashboard").then((r) => setData(r.data)); }, []);

  if (!data) return <div className="p-8 text-slate-400">Carregando...</div>;

  const pie = Object.entries(data.by_status)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ name: k, value: v }));

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Visão geral fiscal">
        <Button onClick={() => navigate("/notas/nova")} data-testid="new-invoice-header-button">
          <Plus size={18} weight="bold" className="mr-1" /> Nova Nota
        </Button>
      </PageHeader>
      <div className="p-8 space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard icon={Receipt} label="Notas Emitidas" value={data.total_notas} tint="bg-blue-100 text-blue-600" delay={0} />
          <StatCard icon={CurrencyDollar} label="Receita" value={money(data.receita)} tint="bg-emerald-100 text-emerald-600" delay={60} />
          <StatCard icon={Percent} label="Impostos" value={money(data.impostos)} tint="bg-amber-100 text-amber-600" delay={120} />
          <StatCard icon={Users} label="Clientes" value={data.clientes} tint="bg-violet-100 text-violet-600" delay={180} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="p-6 border-slate-200 lg:col-span-2">
            <h3 className="text-sm font-semibold text-slate-800 mb-4">Faturamento por mês</h3>
            {data.monthly.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-slate-400 text-sm">Sem dados ainda</div>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.monthly}>
                  <XAxis dataKey="mes" tick={{ fontSize: 12, fill: "#64748B" }} axisLine={{ stroke: "#E2E8F0" }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12, fill: "#64748B" }} axisLine={false} tickLine={false} />
                  <Tooltip formatter={(v) => money(v)} />
                  <Bar dataKey="valor" fill="#2563EB" radius={[4, 4, 0, 0]} maxBarSize={48} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
          <Card className="p-6 border-slate-200">
            <h3 className="text-sm font-semibold text-slate-800 mb-4">Notas por status</h3>
            {pie.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-slate-400 text-sm">Sem dados ainda</div>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie data={pie} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={90} paddingAngle={2}>
                    {pie.map((e, i) => <Cell key={i} fill={STATUS_COLORS[e.name] || "#94A3B8"} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </Card>
        </div>

        <Card className="border-slate-200">
          <div className="p-6 border-b border-slate-200"><h3 className="text-sm font-semibold text-slate-800">Notas recentes</h3></div>
          {data.recentes.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">Nenhuma nota emitida ainda</div>
          ) : (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-100">
                <th className="px-6 py-3">Número</th><th className="px-6 py-3">Cliente</th>
                <th className="px-6 py-3">Valor</th><th className="px-6 py-3">Status</th>
              </tr></thead>
              <tbody>
                {data.recentes.map((r) => (
                  <tr key={r.id} onClick={() => navigate(`/notas/${r.id}`)} className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors" data-testid={`recent-invoice-${r.id}`}>
                    <td className="px-6 py-3 font-medium">#{String(r.numero).padStart(3, "0")}</td>
                    <td className="px-6 py-3 text-slate-600">{r.cliente?.nome}</td>
                    <td className="px-6 py-3">{money(r.totais?.v_nf)}</td>
                    <td className="px-6 py-3"><StatusBadge status={r.status} /></td>
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
