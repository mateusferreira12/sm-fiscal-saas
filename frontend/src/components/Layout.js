import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  ChartPieSlice, Users, Package, Receipt, Gear, SignOut, FileText, ChartBar, SealCheck,
} from "@phosphor-icons/react";

const nav = [
  { to: "/", label: "Dashboard", icon: ChartPieSlice },
  { to: "/notas", label: "Notas Fiscais", icon: Receipt },
  { to: "/clientes", label: "Clientes", icon: Users },
  { to: "/produtos", label: "Produtos", icon: Package },
  { to: "/manifestacao", label: "Manifestação", icon: SealCheck },
  { to: "/relatorios", label: "Relatórios", icon: ChartBar },
  { to: "/configuracoes", label: "Configurações", icon: Gear },
];

export default function Layout({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const isActive = (to) => (to === "/" ? location.pathname === "/" : location.pathname.startsWith(to));

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-background">
      <aside className="w-64 bg-slate-900 text-slate-100 flex flex-col fixed h-screen z-20" data-testid="sidebar">
        <div className="h-16 flex items-center gap-2 px-6 border-b border-slate-800">
          <FileText size={26} weight="duotone" className="text-blue-400" />
          <div>
            <div className="font-bold tracking-tight leading-none">SM Software Solutions</div>
            <div className="text-[10px] uppercase tracking-widest text-slate-500 mt-0.5">Emissão Fiscal</div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-6 space-y-1">
          {nav.map((n) => {
            const Icon = n.icon;
            const active = isActive(n.to);
            return (
              <Link
                key={n.to}
                to={n.to}
                data-testid={`nav-${n.to === "/" ? "dashboard" : n.to.slice(1)}`}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  active ? "bg-blue-600 text-white" : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                <Icon size={20} weight={active ? "fill" : "regular"} />
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-slate-800">
          <div className="px-3 py-2 text-xs text-slate-400 truncate">{user?.email}</div>
          <button
            onClick={handleLogout}
            data-testid="logout-button"
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-slate-300 hover:bg-slate-800 transition-colors"
          >
            <SignOut size={20} />
            Sair
          </button>
        </div>
      </aside>
      <main className="flex-1 ml-64 min-h-screen">{children}</main>
    </div>
  );
}
