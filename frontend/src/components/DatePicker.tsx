const MONTHS = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'];
const DAYS = Array.from({ length: 31 }, (_, i) => String(i + 1).padStart(2, '0'));

function getYears(): number[] {
  const y = new Date().getFullYear();
  return [y, y - 1, y - 2, y - 3, y - 4];
}

interface DatePickerProps {
  value: string;
  onChange: (val: string) => void;
}

export default function DatePicker({ value, onChange }: DatePickerProps) {
  const parts = value ? value.split('-') : ['', '', ''];
  const [y, m, d] = parts;
  const years = getYears();

  const handleY = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const ny = e.target.value;
    const nm = m || '01';
    const nd = d || '01';
    onChange(`${ny}-${nm}-${nd}`);
  };
  const handleM = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const nm = e.target.value;
    const ny = y || String(new Date().getFullYear());
    const nd = d || '01';
    onChange(`${ny}-${nm}-${nd}`);
  };
  const handleD = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const nd = e.target.value;
    const ny = y || String(new Date().getFullYear());
    const nm = m || '01';
    onChange(`${ny}-${nm}-${nd}`);
  };

  return (
    <div className="input-field" style={{ display: 'flex', gap: '0.375rem', padding: '0.25rem 0.375rem', minWidth: 0 }}>
      <select
        value={y}
        onChange={handleY}
        style={{ background: 'transparent', border: 'none', color: 'inherit', flex: '1 1 0', minWidth: 0, outline: 'none', cursor: 'pointer', fontSize: '0.875rem', padding: '0.25rem' }}
      >
        {years.map(yr => (
          <option key={yr} value={yr}>{yr}</option>
        ))}
      </select>
      <span style={{ opacity: 0.4, lineHeight: '2', fontSize: '0.875rem' }}>-</span>
      <select
        value={m}
        onChange={handleM}
        style={{ background: 'transparent', border: 'none', color: 'inherit', flex: '1 1 0', minWidth: 0, outline: 'none', cursor: 'pointer', fontSize: '0.875rem', padding: '0.25rem' }}
      >
        {MONTHS.map((mo, i) => (
          <option key={mo} value={mo}>{String(i + 1).padStart(2, '0')}</option>
        ))}
      </select>
      <span style={{ opacity: 0.4, lineHeight: '2', fontSize: '0.875rem' }}>-</span>
      <select
        value={d}
        onChange={handleD}
        style={{ background: 'transparent', border: 'none', color: 'inherit', flex: '1 1 0', minWidth: 0, outline: 'none', cursor: 'pointer', fontSize: '0.875rem', padding: '0.25rem' }}
      >
        {DAYS.map(dy => (
          <option key={dy} value={dy}>{dy}</option>
        ))}
      </select>
    </div>
  );
}