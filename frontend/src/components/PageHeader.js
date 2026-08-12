export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="h-16 sticky top-0 z-10 bg-white border-b border-slate-200 flex items-center justify-between px-8">
      <div>
        <h1 className="text-lg font-semibold tracking-tight text-slate-900 leading-none">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">{children}</div>
    </div>
  );
}

const STATUS = {
  rascunho: { label: "Rascunho", cls: "bg-slate-100 text-slate-700" },
  pendente: { label: "Pendente", cls: "bg-amber-100 text-amber-700" },
  autorizada: { label: "Autorizada", cls: "bg-emerald-100 text-emerald-700" },
  rejeitada: { label: "Rejeitada", cls: "bg-red-100 text-red-700" },
  cancelada: { label: "Cancelada", cls: "bg-red-100 text-red-700" },
};

export function StatusBadge({ status }) {
  const s = STATUS[status] || STATUS.rascunho;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${s.cls}`} data-testid={`status-${status}`}>
      {s.label}
    </span>
  );
}
