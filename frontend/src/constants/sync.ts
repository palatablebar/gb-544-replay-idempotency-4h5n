import type {
  ConflictStrategy as ConflictStrategyValue,
  ReplayBatchStatus as ReplayBatchStatusValue,
  RunStatus as RunStatusValue,
  SyncMode as SyncModeValue,
  Stage,
} from '../types/models';

export const SyncMode = { FULL: 'full', INCREMENTAL: 'incremental' } as const;
export const SyncModeLabel: Record<SyncModeValue, string> = { full: '全量', incremental: '增量' };

export const RunStatus = {
  QUEUED: 'queued',
  RUNNING: 'running',
  SUCCEEDED: 'succeeded',
  PARTIAL: 'partial',
  FAILED: 'failed',
  CANCELED: 'canceled',
} as const;

export const RunStatusLabel: Record<RunStatusValue, string> = {
  queued: '排队中',
  running: '运行中',
  succeeded: '成功',
  partial: '部分成功',
  failed: '失败',
  canceled: '已取消',
};

export const RunStatusToken: Record<RunStatusValue, string> = {
  queued: 'var(--color-dim)',
  running: 'var(--color-signal)',
  succeeded: 'var(--color-ok)',
  partial: 'var(--color-warn)',
  failed: 'var(--color-danger)',
  canceled: 'var(--color-dim)',
};

export const TERMINAL_STATUSES: RunStatusValue[] = ['succeeded', 'partial', 'failed', 'canceled'];

export const ReplayBatchStatusLabel: Record<ReplayBatchStatusValue, string> = {
  queued: '排队中',
  running: '重放中',
  succeeded: '全部写入',
  partial: '部分写入',
  failed: '重放失败',
};

export const ACTIVE_REPLAY_STATUSES: ReplayBatchStatusValue[] = ['queued', 'running'];

export const ConflictStrategy = { SKIP: 'skip', OVERWRITE: 'overwrite', REJECT: 'reject' } as const;
export const ConflictStrategyLabel: Record<ConflictStrategyValue, string> = {
  skip: '跳过',
  overwrite: '覆盖',
  reject: '拒绝',
};

export const StageOrder: Stage[] = ['probe', 'extract', 'transform', 'load', 'verify'];
export const StageLabel: Record<Stage, string> = {
  probe: '探测',
  extract: '抽取',
  transform: '转换',
  load: '写入',
  verify: '校验',
};

export const TriggerLabel: Record<string, string> = {
  manual: '手动',
  schedule: '调度',
  api: '接口',
};

export const ReasonCodeLabel: Record<string, string> = {
  required_missing: '必填字段缺失',
  type_mismatch: '类型不匹配',
  transform_failed: '转换失败',
  conflict_rejected: '冲突被拒绝',
  constraint_violation: '约束冲突',
};
