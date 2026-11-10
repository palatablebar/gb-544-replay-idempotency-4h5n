export type Role = 'owner' | 'operator' | 'viewer';
export type SourceType = 'csv' | 'jsonl' | 'postgres_table' | 'mock_rest';
export type SourceStatus = 'untested' | 'ok' | 'unreachable';
export type SyncMode = 'full' | 'incremental';
export type RunStatus = 'queued' | 'running' | 'succeeded' | 'partial' | 'failed' | 'canceled';
export type ConflictStrategy = 'skip' | 'overwrite' | 'reject';
export type TransformType =
  | 'trim'
  | 'upper'
  | 'lower'
  | 'date_format'
  | 'number_cast'
  | 'concat'
  | 'default';
export type PipelineStatus = 'draft' | 'active' | 'paused' | 'error';
export type Stage = 'probe' | 'extract' | 'transform' | 'load' | 'verify';
export type ReplayBatchStatus = 'queued' | 'running' | 'succeeded' | 'partial' | 'failed';

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  role_label?: string;
  is_active: boolean;
  max_concurrent_runs: number;
  quota?: { max: number; active: number; remaining: number; global_active: number };
}

export interface SourceRef {
  id: string;
  name: string;
  target_full_name: string;
}

export interface DataSource {
  id: string;
  name: string;
  source_type: SourceType;
  config: Record<string, unknown>;
  status: SourceStatus;
  last_probed_at: string | null;
  probe_result: { columns?: string[]; sample?: Record<string, unknown>[]; row_count?: number; total_pages?: number; note?: string };
  owner_id: string;
  created_at: string | null;
  referenced_pipelines: SourceRef[];
}

export interface SyncRunBrief {
  id: string;
  pipeline_id: string;
  pipeline_name: string | null;
  source_type: SourceType | null;
  trigger_type: 'manual' | 'schedule' | 'api';
  status: RunStatus;
  rows_read: number;
  rows_written: number;
  rows_rejected: number;
  rows_skipped: number;
  rows_triplet: string;
  watermark_from: string | null;
  watermark_value: string | null;
  watermark_text: string;
  stage: Stage;
  stage_history: { stage: string; label?: string; at: string }[];
  error_message: string | null;
  error_code: string | null;
  retry_count: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
  duration_text: string;
}

export interface SyncPipeline {
  id: string;
  name: string;
  owner_id: string;
  source_id: string;
  source_name: string | null;
  source_type: SourceType | null;
  source_status: SourceStatus | null;
  target_schema: string;
  target_table: string;
  target_full_name: string;
  sync_mode: SyncMode;
  watermark_column: string | null;
  conflict_strategy: ConflictStrategy;
  conflict_key: string | null;
  schedule_cron: string | null;
  batch_size: number;
  status: PipelineStatus;
  last_watermark: string | null;
  mapping_count: number;
  created_at: string | null;
  updated_at: string | null;
  last_run: SyncRunBrief | null;
}

export interface FieldMapping {
  id?: string;
  pipeline_id?: string;
  source_field: string;
  target_column: string;
  transform_type: TransformType;
  transform_config: Record<string, unknown>;
  default_value: string | null;
  is_required: boolean;
  order_index: number;
}

export interface RejectedRecord {
  id: string;
  run_id: string;
  pipeline_id: string;
  raw_payload: Record<string, unknown>;
  reason_code: string;
  reason_detail: string;
  source_row_index: number;
  replayed_at: string | null;
  created_at: string | null;
}

export interface ReplayBatchBrief {
  id: string;
  run_id: string;
  status: ReplayBatchStatus;
  total: number;
  processed: number;
  written: number;
  still_rejected: number;
  progress_text: string;
  error_message: string | null;
  created_at: string | null;
  finished_at: string | null;
}

export interface RunDetail extends SyncRunBrief {
  pipeline: {
    id: string;
    name: string;
    target_full_name: string;
    sync_mode: SyncMode;
    watermark_column: string | null;
    conflict_strategy: ConflictStrategy;
    conflict_key: string | null;
  } | null;
  mappings: FieldMapping[];
  rejected: RejectedRecord[];
  rejected_by_reason: Record<string, number>;
  replay_batches: ReplayBatchBrief[];
  diff: {
    source_rows: Record<string, unknown>[];
    target_rows: Record<string, unknown>[];
    target_columns: FieldMapping[];
  };
}

export interface TargetColumn {
  name: string;
  type: string;
  nullable: boolean;
  is_audit: boolean;
}

export interface TargetTable {
  schema: string;
  table: string;
  full_name: string;
  columns: TargetColumn[];
  row_count: number;
  pipeline_id: string | null;
  pipeline_name: string | null;
  conflict_key: string | null;
}

export interface PreviewResult {
  mappings: FieldMapping[];
  samples: { index: number; before: Record<string, unknown>; after: Record<string, unknown> }[];
  failures: { reason_code: string; reason_detail: string }[];
  columns: string[];
}
