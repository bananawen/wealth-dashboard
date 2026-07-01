import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type {
  Transaction,
  CreateTransactionRequest,
  UpdateTransactionRequest,
  ComputedHolding,
  Holding,
  PortfolioSummary,
  PortfolioPerformance,
  HistoryPoint,
  PriceRecord,
  VersionInfo,
  AdminStatus,
  DbStats,
  ScraperStatus,
  ScraperRunResponse,
  MissingDataItem,
  AuditLogResponse,
  LoginRequest,
  LoginResponse,
  TransactionImportResult,
} from '../types';

// Base query with auth header
const baseQuery = fetchBaseQuery({
  baseUrl: '/api',
  prepareHeaders: (headers) => {
    const token = localStorage.getItem('token');
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    return headers;
  },
  jsonContentType: 'application/json',
});

const getRequestUrl = (args: Parameters<typeof fetchBaseQuery>[0]) => {
  if (typeof args === 'string') return args;
  if (args && typeof args === 'object' && 'url' in args && typeof args.url === 'string') return args.url;
  return '';
};

// Handle 401 globally
const baseQueryWithAuth = async (args: Parameters<typeof fetchBaseQuery>[0], api: Parameters<typeof fetchBaseQuery>[1]['api'], extraOptions: Parameters<typeof fetchBaseQuery>[1]['extraOptions']) => {
  const result = await baseQuery(args, { ...api, baseUrl: '/api' } as Parameters<typeof fetchBaseQuery>[1], extraOptions);
  const token = localStorage.getItem('token');
  const url = getRequestUrl(args);
  const isAuthEndpoint = url.startsWith('/auth/login') || url.startsWith('/auth/register');
  if (result.error?.status === 401 && token && !isAuthEndpoint) {
    localStorage.removeItem('token');
    window.location.href = '/login';
  }
  return result;
};

export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithAuth as typeof fetchBaseQuery,
  tagTypes: ['Transaction', 'Holding', 'Portfolio', 'Status', 'AuditLog'],
  endpoints: (builder) => ({
    // ---------- Auth ----------
    login: builder.mutation<LoginResponse, LoginRequest>({
      query: (credentials) => ({
        url: '/auth/login',
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(credentials),
      }),
    }),
    register: builder.mutation<{ message: string }, { username: string; password: string }>({
      query: (body) => ({ url: '/auth/register', method: 'POST', body }),
    }),
    changePassword: builder.mutation<{ message: string }, { old_password: string; new_password: string }>({
      query: (body) => ({ url: '/auth/password', method: 'PUT', body }),
    }),

    // ---------- Transactions ----------
    getTransactions: builder.query<Transaction[], void>({
      query: () => '/transactions',
      providesTags: ['Transaction'],
    }),
    createTransaction: builder.mutation<Transaction, CreateTransactionRequest>({
      query: (body) => ({ url: '/transactions', method: 'POST', body }),
      invalidatesTags: ['Transaction', 'Holding', 'Portfolio'],
    }),
    updateTransaction: builder.mutation<Transaction, { id: number; data: UpdateTransactionRequest }>({
      query: ({ id, data }) => ({ url: `/transactions/${id}`, method: 'PUT', body: data }),
      invalidatesTags: ['Transaction', 'Holding', 'Portfolio'],
    }),
    deleteTransaction: builder.mutation<Transaction, number>({
      query: (id) => ({ url: `/transactions/${id}`, method: 'DELETE' }),
      invalidatesTags: ['Transaction', 'Holding', 'Portfolio'],
    }),
    importTransactions: builder.mutation<TransactionImportResult, FormData>({
      query: (body) => ({ url: '/transactions/import', method: 'POST', body }),
      invalidatesTags: ['Transaction', 'Holding', 'Portfolio'],
    }),

    // ---------- Holdings ----------
    getHoldings: builder.query<Holding[], void>({
      query: () => '/holdings',
      providesTags: ['Holding'],
    }),
       getComputedHoldings: builder.query<ComputedHolding[], void>({
      query: () => '/holdings/computed',
      providesTags: ['Holding'],
      refetchOnMountOrArgChange: true,
      keepUnusedDataFor: 0,
    }),
    // ---------- Portfolio ----------
       getPortfolioSummary: builder.query<PortfolioSummary, void>({
      query: () => '/portfolio/summary',
      providesTags: ['Portfolio'],
      refetchOnMountOrArgChange: true,
      keepUnusedDataFor: 0,
    }),
    getHistory: builder.query<HistoryPoint[], void>({
      query: () => '/portfolio/history',
      providesTags: ['Portfolio'],
    }),
    getPriceHistory: builder.query<PriceRecord[], { market: 'TW' | 'US'; symbol: string; days: number }>({
      query: ({ market, symbol, days }) => `/prices/${market === 'US' ? 'us' : 'tw'}?symbol=${encodeURIComponent(symbol)}&days=${days}`,
      providesTags: ['Portfolio'],
    }),
    getPerformance: builder.query<PortfolioPerformance, { range?: 'today' | 'week' | 'month' | 'year' | 'all' }>({
      query: ({ range = 'all' } = {}) => `/portfolio/performance?range=${range}`,
      providesTags: ['Portfolio'],
    }),
    createSnapshot: builder.mutation<void, { date: string; value: number; value_twd?: number }>({
      query: (body) => ({ url: '/portfolio/snapshot', method: 'POST', body }),
    }),

    // ---------- Admin ----------
    getStatus: builder.query<AdminStatus, void>({
      query: () => '/admin/status',
      providesTags: ['Status'],
    }),
    getVersion: builder.query<VersionInfo, void>({
      query: () => '/admin/version',
    }),
    getDbStats: builder.query<DbStats, void>({
      query: () => '/admin/db/stats',
      providesTags: ['Status'],
    }),
    getScraperStatus: builder.query<ScraperStatus, void>({
      query: () => '/admin/scraper/status',
      providesTags: ['Status'],
    }),
    getScraperRuns: builder.query<ScraperRunResponse[], number | void>({
      query: (limit = 20) => `/admin/scraper/runs?limit=${limit}`,
      providesTags: ['Status', 'AuditLog'],
    }),
    triggerScraper: builder.mutation<{ job_name: string; status: string }, { mode: 'single' | 'all_holdings' | 'backfill_gaps'; symbol?: string }>({
      query: (body) => ({ url: '/admin/scraper/trigger', method: 'POST', body }),
      invalidatesTags: ['Status', 'AuditLog'],
    }),
    setScraperScheduler: builder.mutation<ScraperStatus, { enabled: boolean }>({
      query: (body) => ({ url: '/admin/scraper/scheduler', method: 'POST', body }),
      invalidatesTags: ['Status'],
    }),
    getMissingDataReport: builder.query<MissingDataItem[], void>({
      query: () => '/admin/scraper/missing-data',
      providesTags: ['Status', 'AuditLog'],
    }),
    getAuditLogs: builder.query<AuditLogResponse, { log_type?: string; q?: string; start_date?: string; end_date?: string; limit?: number }>({
      query: ({ log_type = '', q = '', start_date = '', end_date = '', limit = 100 }) => {
        const params = new URLSearchParams();
        if (log_type) params.set('log_type', log_type);
        if (q) params.set('q', q);
        if (start_date) params.set('start_date', start_date);
        if (end_date) params.set('end_date', end_date);
        params.set('limit', String(limit));
        return `/admin/logs?${params.toString()}`;
      },
      providesTags: ['AuditLog'],
    }),
  }),
});

export const {
  useLoginMutation,
  useRegisterMutation,
  useChangePasswordMutation,
  useGetTransactionsQuery,
  useCreateTransactionMutation,
  useUpdateTransactionMutation,
  useDeleteTransactionMutation,
  useImportTransactionsMutation,
  useGetHoldingsQuery,
  useGetComputedHoldingsQuery,
  useGetPortfolioSummaryQuery,
  useGetHistoryQuery,
  useGetPriceHistoryQuery,
  useGetPerformanceQuery,
  useCreateSnapshotMutation,
  useGetStatusQuery,
  useGetVersionQuery,
  useGetDbStatsQuery,
  useGetScraperStatusQuery,
  useGetScraperRunsQuery,
  useTriggerScraperMutation,
  useSetScraperSchedulerMutation,
  useGetMissingDataReportQuery,
  useGetAuditLogsQuery,
} = apiSlice;
