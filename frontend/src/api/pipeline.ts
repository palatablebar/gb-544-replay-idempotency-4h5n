import { api } from './client';
import type { SyncPipeline, SyncRunBrief } from '../types/models';
import type { ListResponse } from '../types/api';

export interface PipelineDraft {
  name: string;
  source_id: string;
  target_table: string;
  target_schema?: string;
  sync_mode?: string;
  watermark_column?: string | null;
  conflict_strategy?: string;
  conflict_key?: string | null;
  schedule_cron?: string | null;
  batch_size?: number;
}

export const pipelineApi = {
  list: () => api.get<ListResponse<SyncPipeline>>('/pipelines'),
  get: (id: string) => api.get<SyncPipeline>(`/pipelines/${id}`),
  create: (payload: PipelineDraft) => api.post<SyncPipeline>('/pipelines', payload),
  update: (id: string, payload: Partial<PipelineDraft>) => api.put<SyncPipeline>(`/pipelines/${id}`, payload),
  remove: (id: string) => api.del<{ ok: boolean }>(`/pipelines/${id}`),
  validate: (id: string) => api.post<{ ok: boolean; mappings: number }>(`/pipelines/${id}/validate`),
  activate: (id: string) => api.post<SyncPipeline>(`/pipelines/${id}/activate`),
  pause: (id: string) => api.post<SyncPipeline>(`/pipelines/${id}/pause`),
  trigger: (id: string) => api.post<SyncRunBrief>(`/pipelines/${id}/trigger`),
  duplicate: (id: string) => api.post<SyncPipeline>(`/pipelines/${id}/duplicate`),
};
