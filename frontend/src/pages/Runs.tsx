import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { pipelineApi } from '../api/pipeline';
import { PipelineTree } from '../components/layout/PipelineTree';
import { RunTimeline } from '../components/layout/RunTimeline';
import { InspectorPanel } from '../components/layout/InspectorPanel';
import { EmptyState } from '../components/common/EmptyState';
import { RunStatusPill } from '../components/common/RunStatusPill';
import { useRunPolling } from '../hooks/useRunPolling';
import { usePipelineStore } from '../stores/pipelineStore';
import { useRunStore } from '../stores/runStore';
import { RunStatusLabel } from '../constants/sync';
import type { RunStatus } from '../types/models';
import { formatTimestamp } from '../utils/formatCount';
import { isNoNewData, watermarkLine } from '../utils/watermark';

const STATUSES: (RunStatus | 'all')[] = ['all', 'queued', 'running', 'succeeded', 'partial', 'failed', 'canceled'];

export const RunsPage = () => {
  const { selectedPipelineId, select, collapsedSources, toggleSource } = usePipelineStore();
  const { statusFilter, setStatusFilter } = useRunStore();
  const runsQuery = useRunPolling(selectedPipelineId ?? undefined, 60);
  const pipelinesQuery = useQuery({ queryKey: ['pipelines'], queryFn: () => pipelineApi.list() });

  const pipelines = pipelinesQuery.data?.items ?? [];
  const runs = useMemo(() => {
    const items = runsQuery.data?.items ?? [];
    return statusFilter === 'all' ? items : items.filter((run) => run.status === statusFilter);
  }, [runsQuery.data?.items, statusFilter]);

  const quota = runsQuery.data?.quota ?? { max: 2, active: 0, remaining: 2 };
  const activeRun = runs.find((run) => run.status === 'running') ?? runs[0];

  return (
    <div className="flex min-h-[calc(100vh-45px)]">
      <PipelineTree
        pipelines={pipelines}
        selectedId={selectedPipelineId}
        collapsedSources={collapsedSources}
        onSelect={select}
        onToggleSource={toggleSource}
      />

      <section className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-3 border-b px-4 py-2" style={{ borderColor: 'var(--color-wire)' }}>
          <div className="label-caps">运行时间线</div>
          <div className="num text-micro text-dim">
            并发占用 {quota.active}/{quota.max}
            {runsQuery.isFetching && <span style={{ color: 'var(--color-signal)' }}> · 轮询中</span>}
          </div>
          <div className="ml-auto flex items-center gap-1">
            {STATUSES.map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className="border px-1.5 py-[1px] text-micro"
                style={{
                  borderColor: statusFilter === status ? 'var(--color-signal)' : 'var(--color-wire)',
                  color: statusFilter === status ? 'var(--color-signal)' : 'var(--color-dim)',
                }}
              >
                {status === 'all' ? '全部' : RunStatusLabel[status]}
              </button>
            ))}
          </div>
        </div>

        {runs.length === 0 ? (
          <EmptyState
            label="还没有运行记录"
            description="还没有运行记录。在管道行尾点『运行一次』，或给管道设一个 cron"
            action={
              <Link to="/pipelines" className="text-micro text-signal">
                去管道清单触发一次
              </Link>
            }
          />
        ) : (
          <RunTimeline runs={runs} selectedId={activeRun?.id ?? null} />
        )}
      </section>

      <InspectorPanel title="检查器 · 当前运行">
        {activeRun ? (
          <div className="space-y-2 text-dense">
            <div className="title-font text-lead text-ink">{activeRun.pipeline_name}</div>
            <RunStatusPill
              status={activeRun.status}
              rows={{ read: activeRun.rows_read, written: activeRun.rows_written, rejected: activeRun.rows_rejected }}
            />
            <div className="num text-micro text-dim">run {activeRun.id.slice(0, 8)}</div>
            <div className="num text-micro text-dim">开始 {formatTimestamp(activeRun.started_at)}</div>
            <div className="num text-micro text-dim">耗时 {activeRun.duration_text}</div>
            <div className="num text-micro text-dim">
              {isNoNewData(activeRun) ? '本批无新数据' : watermarkLine(activeRun.watermark_from, activeRun.watermark_value)}
            </div>
            {activeRun.rows_rejected > 0 && (
              <div className="text-micro" style={{ color: 'var(--color-warn)' }}>
                有 {activeRun.rows_rejected} 行被拒绝，进详情按原因码处理
              </div>
            )}
            {activeRun.error_message && (
              <div className="text-micro" style={{ color: 'var(--color-danger)' }}>
                {activeRun.error_message}
              </div>
            )}
            <Link to={`/runs/${activeRun.id}`} className="inline-block text-micro text-signal">
              打开行级差异与拒绝记录 →
            </Link>
          </div>
        ) : (
          <div className="text-dense text-dim">选择左侧任一管道或等待运行</div>
        )}
      </InspectorPanel>
    </div>
  );
};
