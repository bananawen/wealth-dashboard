import { X } from 'lucide-react';

const MONTHS = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'];
const DAYS = Array.from({ length: 31 }, (_, i) => String(i + 1).padStart(2, '0'));

function getYears(range = 8): number[] {
  const y = new Date().getFullYear();
  return Array.from({ length: range }, (_, index) => y - index);
}

interface DatePickerProps {
  value: string;
  onChange: (val: string) => void;
  allowClear?: boolean;
  yearRange?: number;
  placeholderLabel?: string;
}

export default function DatePicker({
  value,
  onChange,
  allowClear = false,
  yearRange = 8,
  placeholderLabel = '未設定',
}: DatePickerProps) {
  const parts = value ? value.split('-') : ['', '', ''];
  const [y, m, d] = parts;
  const years = getYears(yearRange);

  const handleY = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const ny = e.target.value;
    if (!ny && allowClear) {
      onChange('');
      return;
    }
    const nm = m || '01';
    const nd = d || '01';
    onChange(`${ny}-${nm}-${nd}`);
  };
  const handleM = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const nm = e.target.value;
    if (!nm && allowClear) {
      onChange('');
      return;
    }
    const ny = y || String(new Date().getFullYear());
    const nd = d || '01';
    onChange(`${ny}-${nm}-${nd}`);
  };
  const handleD = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const nd = e.target.value;
    if (!nd && allowClear) {
      onChange('');
      return;
    }
    const ny = y || String(new Date().getFullYear());
    const nm = m || '01';
    onChange(`${ny}-${nm}-${nd}`);
  };

  return (
    <div className="input-field flex min-w-0 items-center gap-1.5 px-2 py-1.5">
      <select
        value={y}
        onChange={handleY}
        className="min-w-0 flex-1 cursor-pointer bg-transparent px-1 py-1 text-sm outline-none"
      >
        {allowClear ? <option value="">{placeholderLabel}</option> : null}
        {years.map(yr => (
          <option key={yr} value={yr}>{yr}</option>
        ))}
      </select>
      <span className="text-sm opacity-40">-</span>
      <select
        value={m}
        onChange={handleM}
        className="min-w-0 flex-1 cursor-pointer bg-transparent px-1 py-1 text-sm outline-none"
      >
        {allowClear ? <option value="">月</option> : null}
        {MONTHS.map((mo, i) => (
          <option key={mo} value={mo}>{String(i + 1).padStart(2, '0')}</option>
        ))}
      </select>
      <span className="text-sm opacity-40">-</span>
      <select
        value={d}
        onChange={handleD}
        className="min-w-0 flex-1 cursor-pointer bg-transparent px-1 py-1 text-sm outline-none"
      >
        {allowClear ? <option value="">日</option> : null}
        {DAYS.map(dy => (
          <option key={dy} value={dy}>{dy}</option>
        ))}
      </select>
      {allowClear && value ? (
        <button
          type="button"
          onClick={() => onChange('')}
          className="shrink-0 rounded p-1 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
          aria-label="清除日期"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      ) : null}
    </div>
  );
}
