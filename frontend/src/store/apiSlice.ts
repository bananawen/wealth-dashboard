import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type {
  Account,
  CreateAccountRequest,
  Transaction,
  CreateTransactionRequest,
  UpdateTransactionRequest,
  ComputedHolding,
  Holding,
  CreateHoldingRequest,
  UpdateHoldingRequest,
  PortfolioSummary,
  HistoryPoint,
  VersionInfo,
  AdminStatus,
  DbStats,
  ScraperStatus,
  AuditLogResponse,
  LoginRequest,
  LoginResponse,
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

// Handle 401 globally
const baseQueryWithAuth = async (args: Parameters<typeof fetchBaseQuery>[0], api: Parameters<typeof fetchBaseQuery>[1]['api'], extraOptions: Parameters<typeof fetchBaseQuery>[1]['extraOptions']) => {
  const result = await baseQuery(args, { ...api, baseUrl: '/api' } as Parameters<typeof fetchBaseQuery>[1], extraOptions);
  if (result.error?.status === 401) {
    localStorage.removeItem('token');
    window.location.href = '/login';
  }
  return result;
};

export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithAuth as typeof fetchBaseQuery,
  tagTypes: ['Account', 'Transaction', 'Holding', 'Portfolio', 'Status', 'AuditLog'],
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

    // ---------- Accounts ----------
    getAccounts: builder.query<Account[], void>({
      query: () => '/accounts',
      providesTags: ['Account'],
    }),
    createAccount: builder.mutation<Account, CreateAccountRequest>({
      query: (body) => ({ url: '/accounts', method: 'POST', body }),
      invalidatesTags: ['Account'],
    }),

    // ---------- Transactions ----------
    getTransactions: builder.query<Transaction[], void>({
      query: () => '/transactions',
      providesTags: ['Transaction'],
    }),
    createTransaction: builder.mutation<{ id: number }, CreateTransactionRequest>({
      query: (body) => ({ url: '/transactions', method: 'POST', body }),
      invalidatesTags: ['Transaction', 'Holding', 'Portfolio'],
    }),
    updateTransaction: builder.mutation<Transaction, { id: number; data: UpdateTransactionRequest }>({
      query: ({ id, data }) => ({ url: `/transactions/${id}`, method: 'PUT', body: data }),
      invalidatesTags: ['Transaction', 'Holding', 'Portfolio'],
    }),
    deleteTransaction: builder.mutation<void, number>({
      query: (id) => ({ url: `/transactions/${id}`, method: 'DELETE' }),
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
    createHolding: builder.mutation<Holding, CreateHoldingRequest>({
      query: (body) => ({ url: '/holdings', method: 'POST', body }),
      invalidatesTags: ['Holding', 'Portfolio'],
    }),
    updateHolding: builder.mutation<Holding, { id: number; data: UpdateHoldingRequest }>({
      query: ({ id, data }) => ({ url: `/holdings/${id}`, method: 'PUT', body: data }),
      invalidatesTags: ['Holding', 'Portfolio'],
    }),
    deleteHolding: builder.mutation<void, number>({
      query: (id) => ({ url: `/holdings/${id}`, method: 'DELETE' }),
      invalidatesTags: ['Holding', 'Portfolio'],
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
    getAuditLogs: builder.query<AuditLogResponse, { log_type?: string; limit?: number }>({
      query: ({ log_type = '', limit = 100 }) =>
        `/admin/logs${log_type ? `?log_type=${log_type}&limit=${limit}` : `?limit=${limit}`}`,
      providesTags: ['AuditLog'],
    }),
  }),
});

export const {
  useLoginMutation,
  useRegisterMutation,
  useChangePasswordMutation,
  useGetAccountsQuery,
  useCreateAccountMutation,
  useGetTransactionsQuery,
  useCreateTransactionMutation,
  useUpdateTransactionMutation,
  useDeleteTransactionMutation,
  useGetHoldingsQuery,
  useGetComputedHoldingsQuery,
  useCreateHoldingMutation,
  useUpdateHoldingMutation,
  useDeleteHoldingMutation,
  useGetPortfolioSummaryQuery,
  useGetHistoryQuery,
  useCreateSnapshotMutation,
  useGetStatusQuery,
  useGetVersionQuery,
  useGetDbStatsQuery,
  useGetScraperStatusQuery,
  useGetAuditLogsQuery,
} = apiSlice;