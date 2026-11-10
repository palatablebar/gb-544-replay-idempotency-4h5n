import { api } from './client';
import type { TargetTable } from '../types/models';
import type { ListResponse } from '../types/api';

export interface TargetRows {
  schema: string;
  table: string;
  columns: { name: string; type: string; nullable: boolean; is_audit: boolean }[];
  total: number;
  page: number;
  page_size: number;
  rows: Record<string, unknown>[];
  pipeline_id: string | null;
}

export const targetApi = {
  list: () => api.get<ListResponse<TargetTable>>('/targets'),
  browse: (schema: string, table: string, params?: { page?: number; page_size?: number; q?: string }) => {
    const query = new URLSearchParams();
    query.set('page', String(params?.page ?? 1));
    query.set('page_size', String(params?.page_size ?? 20));
    if (params?.q) query.set('q', params.q);
    return api.get<TargetRows>(`/targets/${schema}/${table}?${query.toString()}`);
  },
};
