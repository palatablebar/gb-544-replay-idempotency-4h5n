import { api } from './client';
import type { ListResponse } from '../types/api';

export interface ApiKeyRow {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string | null;
}

export const apiKeyApi = {
  list: () => api.get<ListResponse<ApiKeyRow>>('/api-keys'),
  create: (name: string, scopes: string[]) =>
    api.post<ApiKeyRow & { plaintext: string; notice: string }>('/api-keys', { name, scopes }),
  revoke: (id: string) => api.del<{ ok: boolean }>(`/api-keys/${id}`),
};
