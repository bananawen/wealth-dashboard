interface DashboardStatCardProps {
  label: string;
  value: string;
  sub?: string;
  positive?: boolean;
}

export default function DashboardStatCard({ label, value, sub, positive }: DashboardStatCardProps) {
  return (
    <div className="card min-w-0 p-3 sm:p-4 animate-fade-in">
      <div className="truncate text-xs opacity-60 sm:text-sm">{label}</div>
      <div className={`mt-1 truncate text-lg font-bold sm:text-2xl ${positive === undefined ? 'text-inherit' : positive ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
        {value}
      </div>
      {sub ? <div className="mt-1 truncate text-xs opacity-50">{sub}</div> : null}
    </div>
  );
}
