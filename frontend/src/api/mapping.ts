import { api } from './client';
import type { FieldMapping, PreviewResult } from '../types/models';

export interface MappingListResponse {
  pipeline_id: string;
  target_columns: string[];
  items: FieldMapping[];
}

export const mappingApi = {
  list: (pipelineId: string) => api.get<MappingListResponse>(`/pipelines/${pipelineId}/mappings`),
  save: (pipelineId: string, mappings: FieldMapping[]) =>
    api.put<{ items: FieldMapping[]; ok: boolean }>(`/pipelines/${pipelineId}/mappings`, { mappings }),
  preview: (pipelineId: string, mappings: FieldMapping[], limit = 20) =>
    api.post<PreviewResult>(`/pipelines/${pipelineId}/mappings/preview`, { mappings, limit }),
  fill: (pipelineId: string) => api.get<{ items: FieldMapping[] }>(`/pipelines/${pipelineId}/mappings/fill`),
};
