import { api } from './client';
import type { RejectedRecord } from '../types/models';

export const rejectedApi = {
  list: (runId: string, params?: { reason_code?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.reason_code) query.set('reason_code', params.reason_code);
    query.set('page', String(params?.page ?? 1));
    query.set('page_size', String(params?.page_size ?? 50));
    return api.get<{
      items: RejectedRecord[];
      total: number;
      page: number;
      page_size: number;
      by_reason: Record<string, number>;
    }>(`/runs/${runId}/rejected?${query.toString()}`);
  },
  replayOne: (id: string) => api.post<{ queued: number }>(`/rejected/${id}/replay`),
};
