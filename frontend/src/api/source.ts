import { api } from './client';
import type { DataSource, SourceType } from '../types/models';
import type { ListResponse } from '../types/api';

export const sourceApi = {
  list: () => api.get<ListResponse<DataSource>>('/sources'),
  get: (id: string) => api.get<DataSource>(`/sources/${id}`),
  create: (payload: { name: string; source_type: SourceType; config: Record<string, unknown> }) =>
    api.post<DataSource>('/sources', payload),
  update: (id: string, payload: { name?: string; config?: Record<string, unknown> }) =>
    api.put<DataSource>(`/sources/${id}`, payload),
  remove: (id: string) => api.del<{ ok: boolean }>(`/sources/${id}`),
  probe: (id: string) => api.post<{ ok: boolean; probe: Record<string, unknown> }>(`/sources/${id}/probe`),
  sample: (id: string) => api.get<{ columns: string[]; rows: Record<string, unknown>[]; total: number }>(`/sources/${id}/sample`),
  upload: (file: File, sourceType: string) => {
    const form = new FormData();
    form.append('file', file);
    form.append('source_type', sourceType);
    return api.upload<{ upload_path: string; filename: string; checksum: string; size_bytes: number }>('/sources/upload', form);
  },
};
