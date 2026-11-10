import { api } from './client';
import type { ReplayBatchStatus, RunDetail, SyncRunBrief } from '../types/models';
import type { ListResponse } from '../types/api';

export interface ReplayResponse {
  queued: number;
  run_id: string;
  batch_id: string;
  status: ReplayBatchStatus;
  deduplicated: boolean;
}

export const runApi = {
  list: (params?: { status?: string; pipeline_id?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.pipeline_id) query.set('pipeline_id', params.pipeline_id);
    query.set('limit', String(params?.limit ?? 50));
    return api.get<ListResponse<SyncRunBrief> & { quota: { max: number; active: number; remaining: number } }>(
      `/runs?${query.toString()}`,
    );
  },
  detail: (id: string) => api.get<RunDetail>(`/runs/${id}`),
  cancel: (id: string) => api.post<SyncRunBrief>(`/runs/${id}/cancel`),
  replay: (id: string, payload: { rejected_ids?: string[]; reason_code?: string | null }) =>
    api.post<ReplayResponse>(`/runs/${id}/replay`, payload),
};
