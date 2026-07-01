import { useId, useState } from 'react';

interface PasswordFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  autoComplete?: string;
  minLength?: number;
  required?: boolean;
  helperText?: string;
}

export default function PasswordField({
  label,
  value,
  onChange,
  placeholder,
  autoComplete,
  minLength,
  required = false,
  helperText,
}: PasswordFieldProps) {
  const [showPassword, setShowPassword] = useState(false);
  const inputId = useId();

  return (
    <div>
      <label htmlFor={inputId} className="block text-[var(--text-secondary)] text-sm mb-1">
        {label}
        {helperText && <span className="ml-2 text-xs text-[var(--text-secondary)]">{helperText}</span>}
      </label>
      <div className="relative">
        <input
          id={inputId}
          type={showPassword ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-4 py-3 pr-20 text-[var(--text-primary)] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/45 focus:border-[var(--accent)]"
          placeholder={placeholder}
          autoComplete={autoComplete}
          minLength={minLength}
          required={required}
        />
        <button
          type="button"
          onClick={() => setShowPassword(prev => !prev)}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-xs px-2 py-1 rounded-md text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-primary)] transition-colors"
          aria-label={showPassword ? '隱藏密碼' : '顯示密碼'}
        >
          {showPassword ? '隱藏' : '顯示'}
        </button>
      </div>
    </div>
  );
}
