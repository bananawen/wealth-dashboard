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

// ---------- Transaction ----------
export type TransactionType = 'buy' | 'sell';
export type TransactionCategory = 'long_term' | 'short_term' | 'etf' | 'stock' | 'dca';
export type AssetClass = 'equity' | 'bond' | 'precious_metal' | 'cash' | 'other';
export type Sector =
  | 'semiconductor'
  | 'technology'
  | 'financial'
  | 'communication'
  | 'consumer'
  | 'industrial'
  | 'healthcare'
  | 'energy'
  | 'materials'
  | 'utilities'
  | 'real_estate'
  | 'broad_market'
  | 'high_dividend'
  | 'thematic'
  | 'other';

export interface Transaction {
  id: number;
  symbol: string;
  type: TransactionType;
  shares: number;
  price: number;
  date: string; // YYYY-MM-DD
  notes?: string | null;
  category?: TransactionCategory | null;
  asset_class?: AssetClass | null;
  sector?: Sector | null;
  fee?: number;
  tax?: number;
  realized_gain: number;
  created_at?: string;
}

export interface CreateTransactionRequest {
  symbol: string;
  type: TransactionType;
  shares: number;
  price: number;
  date: string;
  notes?: string | null;
  category?: TransactionCategory | null;
  asset_class?: AssetClass | null;
  sector?: Sector | null;
  fee?: number;
  tax?: number;
}

export interface UpdateTransactionRequest extends Partial<CreateTransactionRequest> {}

export interface TransactionImportResult {
  created: number;
  skipped: number;
  errors: string[];
}

// ---------- Holding ----------
export interface Holding {
  id: number;
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
  current_price_twd?: number;
  day_change?: number;
  day_change_twd?: number;
  day_change_pct?: number;
  currency?: string;
  exchange?: string;
  price_source?: string;
  price_status?: 'live' | 'estimated' | 'missing';
  price_is_estimated?: boolean;
}

export interface CreateHoldingRequest {
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
  total_value_by_currency?: Record<string, number>;
  total_cost: number;
  total_cost_twd?: number;
  total_cost_by_currency?: Record<string, number>;
  unrealized_gain: number;
  unrealized_gain_twd?: number;
  unrealized_gain_by_currency?: Record<string, number>;
  unrealized_pct: number;
  realized_gain: number;
  realized_gain_twd?: number;
  realized_gain_by_currency?: Record<string, number>;
  realized_pct: number;
  annualized_return: number | null;
  annualized_return_status?: 'ok' | 'estimated' | 'insufficient_data' | 'failed';
  annualized_return_message?: string | null;
  fx_rate?: number;
  last_updated?: string;
}

// ---------- History / NAV ----------
export interface HistoryPoint {
  date: string;
  value: number;
  value_twd?: number;
}

export interface PriceRecord {
  symbol: string;
  price_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  currency: string;
}

export interface PerformancePoint {
  date: string;
  value: number;
  normalized_value: number;
}

export interface BenchmarkSeries {
  name: string;
  symbol: string;
  market: string;
  points: PerformancePoint[];
}

export interface PortfolioPerformance {
  range: 'today' | 'week' | 'month' | 'year' | 'all';
  start_date: string;
  end_date: string;
  portfolio: PerformancePoint[];
  benchmarks: BenchmarkSeries[];
}

// ---------- Version ----------
export interface VersionInfo {
  version: string;
  last_updated?: string;
  deployed_at?: string;
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

export interface ScraperRunInfo {
  id: number;
  timestamp: string;
  level: string;
  message: string;
  symbol?: string | null;
  job_name: string;
  trigger: string;
  target: string;
  status: 'running' | 'success' | 'warning' | 'error';
  success_count: number;
  failure_count: number;
  records_fetched: number;
  duration_ms?: number | null;
  error_reason?: string | null;
  details?: Record<string, unknown>;
}

export interface ScraperRuntimeRun {
  run_id: string;
  job_name: string;
  trigger: string;
  target: string;
  symbol?: string | null;
  status: 'running' | 'success' | 'warning' | 'error';
  started_at: string;
  finished_at?: string | null;
  duration_ms?: number | null;
  success_count: number;
  failure_count: number;
  records_fetched: number;
  error_reason?: string | null;
  details?: Record<string, unknown>;
}

export interface MissingDataItem {
  symbol: string;
  currency: string;
  region: string;
  latest_price_date?: string | null;
  gap_days?: number | null;
  missing_days: number;
  history_rows: number;
  status: 'fresh' | 'stale' | 'missing';
}

export interface AdminStatus {
  connected: boolean;
  tables: TableInfo[];
  scrapers: ScraperInfo[];
  price_sources?: Array<{
    name: string;
    status: string;
    last_run?: string | null;
    records_fetched?: number;
    message?: string | null;
  }>;
  recent_runs?: ScraperRunInfo[];
  database_size_bytes?: number;
  database_size_mb?: number;
  database_path?: string | null;
  scraper_enabled?: boolean;
  scraper_running?: boolean;
  runtime?: ScraperStatus;
  version?: VersionInfo;
}

export interface DbStats {
  total_size_bytes?: number;
  total_size_mb: number;
  table_count: number;
  tables: TableInfo[];
  last_vacuum?: string;
  last_analyze?: string;
}

export interface ScraperStatus {
  enabled: boolean;
  running: boolean;
  active_runs: ScraperRuntimeRun[];
  recent_runs: ScraperRuntimeRun[];
  last_error?: string | null;
  scheduler_started: boolean;
  timezone: string;
  next_runs: {
    id: string;
    name: string;
    next_run_time?: string | null;
    trigger: string;
  }[];
}

export interface ScraperRunResponse {
  id: number;
  timestamp: string;
  level: string;
  message: string;
  symbol?: string | null;
  job_name: string;
  trigger: string;
  target: string;
  status: 'running' | 'success' | 'warning' | 'error';
  success_count: number;
  failure_count: number;
  records_fetched: number;
  duration_ms?: number | null;
  error_reason?: string | null;
  details: Record<string, unknown>;
}

// ---------- Audit Logs ----------
export type LogType = 'scraper' | 'transaction' | 'auth' | 'admin';

export interface AuditLog {
  id: number;
  type: LogType;
  raw_type?: string;
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
  symbol?: string | null;
  user_id?: number | null;
  level?: string | null;
}

export interface AuditLogResponse {
  logs: AuditLog[];
  total: number;
}

// ---------- Undo Stack ----------
export interface CreateUndoEntry {
  type: 'create';
  id: number;
}

export interface DeleteUndoEntry {
  type: 'delete';
  transaction: Transaction;
  expiresAt: number;
}

export type UndoEntry = CreateUndoEntry | DeleteUndoEntry;

// ---------- API Error ----------
export interface ApiError {
  detail: string;
}

// ---------- Form State ----------
export interface TransactionFormState {
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
