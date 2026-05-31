// ============================================================
// Comprehensive TypeScript Types for Wealth Frontend
// ============================================================

// ---------- Theme ----------
export type Theme = 'light' | 'dark';

export interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
  isDark: boolean;
}

// ---------- Auth ----------
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
}

// ---------- Account ----------
export interface Account {
  id: number;
  name: string;
  type: string; // 'brokerage' | 'crypto' | 'bank' | ...
  currency: string;
  created_at?: string;
}

export interface CreateAccountRequest {
  name: string;
  type: string;
  currency: string;
}

// ---------- Transaction ----------
export type TransactionType = 'buy' | 'sell';

export interface Transaction {
  id: number;
  account_id: number;
  symbol: string;
  type: TransactionType;
  shares: number;
  price: number;
  date: string; // YYYY-MM-DD
  created_at?: string;
}

export interface CreateTransactionRequest {
  account_id: number;
  symbol: string;
  type: TransactionType;
  shares: number;
  price: number;
  date: string;
}

export interface UpdateTransactionRequest extends Partial<CreateTransactionRequest> {}

// ---------- Holding ----------
export interface Holding {
  id: number;
  account_id: number;
  symbol: string;
  shares: number;
  cost_basis: number;
  purchase_date: string;
  created_at?: string;
}

export interface ComputedHolding {
  symbol: string;
  shares: number;
  avg_cost: number;
  total_cost: number;
  total_cost_twd?: number;
  market_value: number;
  market_value_twd?: number;
  unrealized_gain: number;
  unrealized_gain_twd?: number;
  unrealized_pct: number;
  current_price?: number;
  day_change_pct?: number;
  currency?: string;
  exchange?: string;
}

export interface CreateHoldingRequest {
  account_id: number;
  symbol: string;
  shares: number;
  avg_cost: number;
  currency: string;
}

export interface UpdateHoldingRequest extends Partial<CreateHoldingRequest> {}

// ---------- Portfolio Summary ----------
export interface PortfolioSummary {
  total_value: number;
  total_value_twd?: number;
  total_cost: number;
  total_cost_twd?: number;
  unrealized_gain: number;
  unrealized_gain_twd?: number;
  unrealized_pct: number;
  realized_gain: number;
  realized_gain_twd?: number;
  realized_pct: number;
  annualized_return: number | null;
  fx_rate?: number;
  last_updated?: string;
}

// ---------- History / NAV ----------
export interface HistoryPoint {
  date: string;
  value: number;
  value_twd?: number;
}

// ---------- Version ----------
export interface VersionInfo {
  version: string;
  last_updated?: string;
}

// ---------- Admin / Status ----------
export interface TableInfo {
  table_name: string;
  row_count: number;
  size_bytes: number;
  date_range?: string;
}

export interface ScraperInfo {
  name: string;
  status: 'idle' | 'running' | 'error' | 'success';
  last_run?: string;
  next_run?: string;
  error_message?: string;
}

export interface AdminStatus {
  connected: boolean;
  tables: TableInfo[];
  scrapers: ScraperInfo[];
}

export interface DbStats {
  total_size_mb: number;
  table_count: number;
  tables: TableInfo[];
  last_vacuum?: string;
  last_analyze?: string;
}

export interface ScraperStatus {
  scrapers: ScraperInfo[];
  next_scheduled_run?: {
    us_market: string;
    tw_market: string;
  };
}

// ---------- Audit Logs ----------
export type LogType = 'scrape' | 'db_change' | 'api_call' | 'error';

export interface AuditLog {
  id: number;
  type: LogType;
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

export interface AuditLogResponse {
  logs: AuditLog[];
  total: number;
}

// ---------- Undo Stack ----------
export interface UndoEntry {
  type: 'create';
  id: number;
}

// ---------- Dashboard Tab ----------
export type DashboardTab = 'portfolio' | 'transactions' | 'add';

// ---------- API Error ----------
export interface ApiError {
  detail: string;
}

// ---------- Form State ----------
export interface TransactionFormState {
  account_id: string;
  symbol: string;
  type: TransactionType | '';
  shares: string;
  price: string;
  date: string;
}

// ---------- Component Props ----------
export interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string | number;
  positive?: boolean;
}

export interface LogTypeBadgeProps {
  type: LogType;
}

// ---------- Redux-toolkit dispatch hack ----------
// toggleTheme from createSlice returns PayloadAction<void>
// We use this marker to help TypeScript understand the dispatch
export type AnyAction = {
  type: string;
  payload?: unknown;
};