import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { pipelineApi } from '../api/pipeline';
import { PipelineTree } from '../components/layout/PipelineTree';
import { InspectorPanel } from '../components/layout/InspectorPanel';
import { RunStatusPill } from '../components/common/RunStatusPill';
import { EmptyState } from '../components/common/EmptyState';
import { usePipelineStore } from '../stores/pipelineStore';
import { useAuthStore } from '../stores/authStore';
import { useRunPolling } from '../hooks/useRunPolling';
import { ConflictStrategyLabel, SyncModeLabel } from '../constants/sync';
import { cronText } from '../utils/cronText';
import { formatTimestamp } from '../utils/formatCount';
import { toHumanMessage } from '../utils/errorMessage';
import { isNoNewData, watermarkLine } from '../utils/watermark';

export const PipelinesPage = () => {
  const queryClient = useQueryClient();
  const canWrite = useAuthStore((state) => state.can)('pipelines:write');
  const canTrigger = useAuthStore((state) => state.can)('runs:trigger');
  const { selectedPipelineId, select, collapsedSources, toggleSource } = usePipelineStore();
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pipelinesQuery = useQuery({ queryKey: ['pipelines'], queryFn: () => pipelineApi.list() });
  const runsQuery = useRunPolling(undefined, 40);
  const pipelines = pipelinesQuery.data?.items ?? [];
  const runs = runsQuery.data?.items ?? [];
  const selected = pipelines.find((item) => item.id === selectedPipelineId) ?? pipelines[0];
  const pipelineRuns = useMemo(
    () => (selected ? runs.filter((run) => run.pipeline_id === selected.id) : []),
    [runs, selected],
  );

  const act = async (action: 'trigger' | 'activate' | 'pause' | 'duplicate') => {
    if (!selected) return;
    setBusy(action);
    setNotice(null);
    setError(null);
    try {
      if (action === 'trigger') {
        const run = await pipelineApi.trigger(selected.id);
        setNotice(`已入队：${run.id.slice(0, 8)} · 去看运行时间线`);
      } else if (action === 'activate') {
        await pipelineApi.activate(selected.id);
        setNotice('已启用，cron 生效');
      } else if (action === 'pause') {
        await pipelineApi.pause(selected.id);
        setNotice('已暂停调度');
      } else {
        const clone = await pipelineApi.duplicate(selected.id);
        setNotice(`已复制为 ${clone.name}`);
      }
      await queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      await runsQuery.refetch();
    } catch (err) {
      setError(toHumanMessage(err));
    } finally {
      setBusy(null);
    }
  };

  if (pipelines.length === 0) {
    return (
      <EmptyState
        label="管道清单"
        description="还没有管道。选一个源 → 填目标表 → 去映射页配字段，三步就能跑第一次全量"
      />
    );
  }

  return (
    <div className="flex min-h-[calc(100vh-45px)]">
      <PipelineTree
        pipelines={pipelines}
        selectedId={selected?.id ?? null}
        collapsedSources={collapsedSources}
        onSelect={select}
        onToggleSource={toggleSource}
      />

      <section className="min-w-0 flex-1">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b px-4 py-2.5" style={{ borderColor: 'var(--color-wire)' }}>
          <div>
            <div className="title-font text-lead text-ink">{selected?.name}</div>
            <div className="num text-micro text-dim">
              {selected?.target_full_name} · {SyncModeLabel[selected?.sync_mode ?? 'incremental']} · 水位线 {selected?.watermark_column ?? '—'}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to={`/pipelines/${selected?.id}/mapping`}
              className="border px-2 py-1 text-micro"
              style={{ borderColor: 'var(--color-wire)', color: 'var(--color-dim)' }}
            >
              去映射页
            </Link>
            <button
              className="border px-2 py-1 text-micro"
              style={{ borderColor: 'var(--color-signal)', color: 'var(--color-signal)' }}
              disabled={!canTrigger || busy !== null}
              onClick={() => void act('trigger')}
            >
              {busy === 'trigger' ? '触发中…' : '运行一次'}
            </button>
          </div>
        </div>

        {(notice || error) && (
          <div className="border-b px-4 py-1.5 text-micro" style={{ borderColor: 'var(--color-wire)' }}>
            {error ? <span style={{ color: 'var(--color-danger)' }}>{error}</span> : <span className="text-dim">{notice}</span>}
          </div>
        )}

        <div className="grid grid-cols-2 gap-0 lg:grid-cols-4">
          {[
            ['冲突策略', ConflictStrategyLabel[selected?.conflict_strategy ?? 'skip']],
            ['冲突键', selected?.conflict_key ?? '—'],
            ['调度', cronText(selected?.schedule_cron)],
            ['状态', selected?.status ?? '—'],
          ].map(([label, value]) => (
            <div key={label} className="border-b border-r px-4 py-2" style={{ borderColor: 'var(--color-wire)' }}>
              <div className="label-caps">{label}</div>
              <div className="num text-dense text-ink">{value}</div>
            </div>
          ))}
        </div>

        <div className="px-4 py-3">
          <div className="label-caps mb-2">最近运行 · 本管道 {pipelineRuns.length} 条</div>
          {pipelineRuns.length === 0 ? (
            <p className="text-dense text-dim">还没有运行记录。在管道行尾点『运行一次』，或给管道设一个 cron</p>
          ) : (
            <table className="grid-table">
              <thead>
                <tr>
                  <th className="time-col">时间</th>
                  <th style={{ width: 90 }}>触发</th>
                  <th style={{ width: 220 }}>状态 / 读·写·拒</th>
                  <th style={{ width: 70 }}>耗时</th>
                  <th>水位线</th>
                </tr>
              </thead>
              <tbody>
                {pipelineRuns.slice(0, 12).map((run, index) => (
                  <tr key={run.id} className="stagger-row" style={{ animationDelay: `${index * 18}ms` }}>
                    <td className="time-col num text-micro text-dim">{formatTimestamp(run.created_at)}</td>
                    <td className="text-micro text-dim">{run.trigger_type}</td>
                    <td>
                      <RunStatusPill
                        status={run.status}
                        rows={{ read: run.rows_read, written: run.rows_written, rejected: run.rows_rejected }}
                      />
                    </td>
                    <td className="num text-micro text-dim">{run.duration_text}</td>
                    <td className="num text-micro text-dim">
                      {isNoNewData(run) ? '本批无新数据' : watermarkLine(run.watermark_from, run.watermark_value)}
                      <Link to={`/runs/${run.id}`} className="ml-3 text-signal">
                        详情
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <InspectorPanel title="检查器 · 管道动作" hint="只有 owner 能改源配置与删管道；operator 可改映射、触发、重放。">
        <div className="space-y-2 text-dense">
          <div className="flex justify-between">
            <span className="text-dim">映射行数</span>
            <span className="num">{selected?.mapping_count ?? 0}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-dim">上次水位线</span>
            <span className="num truncate">{selected?.last_watermark ?? '（初始）'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-dim">最近运行</span>
            <span className="num">{selected?.last_run ? selected.last_run.duration_text : '—'}</span>
          </div>
        </div>
        <div className="mt-4 space-y-1.5">
          <button
            className="w-full border px-2 py-1 text-micro"
            style={{ borderColor: 'var(--color-wire)', color: 'var(--color-dim)' }}
            disabled={!canWrite || busy !== null}
            onClick={() => void act(selected?.status === 'active' ? 'pause' : 'activate')}
          >
            {selected?.status === 'active' ? '暂停调度' : '启用调度'}
          </button>
          <button
            className="w-full border px-2 py-1 text-micro"
            style={{ borderColor: 'var(--color-wire)', color: 'var(--color-dim)' }}
            disabled={!canWrite || busy !== null}
            onClick={() => void act('duplicate')}
          >
            复制为新管道
          </button>
        </div>
        <div className="mt-4 border-t pt-2 text-micro leading-5 text-dim" style={{ borderColor: 'var(--color-wire)' }}>
          当前用户并发占用 {runsQuery.data?.quota.active ?? 0}/{runsQuery.data?.quota.max ?? 2}；
          同一条管道同一时间只允许一次运行（DB 管道锁）。
        </div>
      </InspectorPanel>
    </div>
  );
};
