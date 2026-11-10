import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { runApi } from '../api/run';
import { rejectedApi } from '../api/rejected';
import { DiffPanel } from '../components/common/DiffPanel';
import { SampleDataGrid } from '../components/common/SampleDataGrid';
import { RunStatusPill } from '../components/common/RunStatusPill';
import { MappingRowEditor } from '../components/common/MappingRowEditor';
import { useAuthStore } from '../stores/authStore';
import { useRunPolling } from '../hooks/useRunPolling';
import { ReasonCodeLabel, StageLabel, StageOrder, RunStatusLabel } from '../constants/sync';
import { formatTimestamp } from '../utils/formatCount';
import { isNoNewData, watermarkLine } from '../utils/watermark';
import { toHumanMessage } from '../utils/errorMessage';

export const RunDetailPage = () => {
  const { id = '' } = useParams();
  const queryClient = useQueryClient();
  const canReplay = useAuthStore((state) => state.can)('runs:replay');
  const [reasonFilter, setReasonFilter] = useState<string>('');
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [diffIndex, setDiffIndex] = useState(0);
  const [onlyDiff, setOnlyDiff] = useState(true);

  useRunPolling(undefined, 10);
  const runQuery = useQuery({ queryKey: ['run', id], queryFn: () => runApi.detail(id), refetchInterval: 2000 });
  const run = runQuery.data;

  const rejectedQuery = useQuery({
    queryKey: ['rejected', id, reasonFilter],
    queryFn: () => rejectedApi.list(id, { reason_code: reasonFilter || undefined }),
  });

  const rejected = rejectedQuery.data?.items ?? [];
  const byReason = rejectedQuery.data?.by_reason ?? run?.rejected_by_reason ?? {};
  const stageIndex = useMemo(() => (run ? StageOrder.indexOf(run.stage) : 0), [run]);

  const replay = async (ids?: string[]) => {
    setBusy(true);
    setError(null);
    try {
      const result = await runApi.replay(id, { rejected_ids: ids ?? [] });
      setMessage(`已排期重放 ${result.queued} 条，刷新查看结果`);
      await queryClient.invalidateQueries({ queryKey: ['run', id] });
      await queryClient.invalidateQueries({ queryKey: ['rejected', id] });
      setTimeout(() => void queryClient.invalidateQueries({ queryKey: ['run', id] }), 1500);
    } catch (err) {
      setError(toHumanMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (!run) {
    return <div className="px-6 py-8 text-dense text-dim">加载运行 {id} …</div>;
  }

  const sourceRow = run.diff.source_rows[diffIndex] ?? {};
  const targetRow = run.diff.target_rows[diffIndex] ?? {};

  return (
    <div className="min-h-[calc(100vh-45px)]">
      <div className="flex flex-wrap items-center gap-3 border-b px-4 py-2" style={{ borderColor: 'var(--color-wire)' }}>
        <Link to="/runs" className="text-micro text-dim hover:text-signal">
          ← 运行时间线
        </Link>
        <div className="title-font text-lead text-ink">{run.pipeline_name}</div>
        <RunStatusPill status={run.status} rows={{ read: run.rows_read, written: run.rows_written, rejected: run.rows_rejected }} />
        <div className="num text-micro text-dim">
          {run.trigger_type} · {formatTimestamp(run.started_at)} · {run.duration_text} · retry {run.retry_count}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            className="border px-2 py-1 text-micro"
            style={{ borderColor: 'var(--color-signal)', color: 'var(--color-signal)' }}
            disabled={!canReplay || busy || rejected.length === 0}
            onClick={() => void replay()}
          >
            {busy ? '提交中…' : `批量重放 ${rejected.length} 条`}
          </button>
        </div>
      </div>

      {(message || error) && (
        <div className="border-b px-4 py-1.5 text-micro" style={{ borderColor: 'var(--color-wire)' }}>
          {error ? <span style={{ color: 'var(--color-danger)' }}>{error}</span> : <span className="text-dim">{message}</span>}
        </div>
      )}

      {/* 阶段步进 + 行数账目 */}
      <div className="flex flex-wrap items-center gap-0 border-b" style={{ borderColor: 'var(--color-wire)' }}>
        {StageOrder.map((stage, index) => {
          const done = index < stageIndex || run.status !== 'running';
          const current = index === stageIndex && run.status === 'running';
          return (
            <div
              key={stage}
              className="flex items-center gap-2 border-r px-3 py-2"
              style={{ borderColor: 'var(--color-wire)' }}
            >
              <span
                className={current ? 'node-live inline-block h-1.5 w-1.5' : 'inline-block h-1.5 w-1.5'}
                style={{ backgroundColor: done ? 'var(--color-ok)' : 'var(--color-wire)' }}
              />
              <span className="text-micro text-dim">{StageLabel[stage]}</span>
            </div>
          );
        })}
        <div className="px-3 py-2 text-micro text-dim">
          读 <span className="num text-ink">{run.rows_read}</span> · 写{' '}
          <span className="num text-ink">{run.rows_written}</span> · 拒{' '}
          <span className="num" style={{ color: run.rows_rejected ? 'var(--color-warn)' : 'var(--color-dim)' }}>
            {run.rows_rejected}
          </span>{' '}
          · 跳过 <span className="num">{run.rows_skipped}</span>
        </div>
        <div className="ml-auto px-3 py-2 text-micro text-dim">
          {isNoNewData(run) ? '本批无新数据' : watermarkLine(run.watermark_from, run.watermark_value)}
        </div>
      </div>

      {run.error_message && (
        <div className="border-b px-4 py-2 text-dense" style={{ borderColor: 'var(--color-wire)', color: 'var(--color-danger)' }}>
          错误 {run.error_code}：{run.error_message}
        </div>
      )}

      <div className="grid grid-cols-1 gap-0 xl:grid-cols-[1.15fr_1fr]">
        <section className="border-b border-r px-4 py-3" style={{ borderColor: 'var(--color-wire)' }}>
          <div className="mb-2 flex items-center gap-3">
            <div className="label-caps">行级差异 · 源 vs 落库</div>
            <label className="text-micro text-dim">
              <input type="checkbox" className="mr-1 h-3 w-3" checked={onlyDiff} onChange={(event) => setOnlyDiff(event.target.checked)} />
              只看差异行
            </label>
            <div className="ml-auto flex items-center gap-1 text-micro text-dim">
              {run.diff.source_rows.slice(0, 8).map((_, index) => (
                <button
                  key={index}
                  onClick={() => setDiffIndex(index)}
                  className="border px-1"
                  style={{
                    borderColor: diffIndex === index ? 'var(--color-signal)' : 'var(--color-wire)',
                    color: diffIndex === index ? 'var(--color-signal)' : 'var(--color-dim)',
                  }}
                >
                  {index + 1}
                </button>
              ))}
            </div>
          </div>
          {run.diff.source_rows.length === 0 ? (
            <p className="text-dense text-dim">本次运行没有可对照的源样本（可能源已不可达或本批无新数据）。</p>
          ) : (
            <DiffPanel sourceRow={sourceRow} targetRow={targetRow} mappings={run.mappings} showOnlyDiff={onlyDiff} />
          )}

          <div className="mt-4">
            <div className="label-caps mb-1">写入样本</div>
            <SampleDataGrid
              columns={run.mappings.map((mapping) => mapping.target_column)}
              rows={run.diff.target_rows}
              emptyHint="目标表里还没有本次运行写入的行"
            />
          </div>
        </section>

        <section className="border-b px-4 py-3" style={{ borderColor: 'var(--color-wire)' }}>
          <div className="mb-2 flex items-center gap-2">
            <div className="label-caps">拒绝记录 · {rejected.length}</div>
            <button
              className="border px-1 text-micro"
              style={{ borderColor: !reasonFilter ? 'var(--color-signal)' : 'var(--color-wire)', color: !reasonFilter ? 'var(--color-signal)' : 'var(--color-dim)' }}
              onClick={() => setReasonFilter('')}
            >
              全部
            </button>
            {Object.entries(byReason).map(([code, count]) => (
              <button
                key={code}
                className="border px-1 text-micro"
                style={{
                  borderColor: reasonFilter === code ? 'var(--color-signal)' : 'var(--color-wire)',
                  color: reasonFilter === code ? 'var(--color-signal)' : 'var(--color-dim)',
                }}
                onClick={() => setReasonFilter(code)}
              >
                {ReasonCodeLabel[code] ?? code} {count}
              </button>
            ))}
          </div>

          {rejected.length === 0 ? (
            <p className="text-dense text-dim">没有拒绝行。status={RunStatusLabel[run.status]}</p>
          ) : (
            <div className="max-h-[420px] overflow-y-auto">
              {rejected.map((record) => (
                <div key={record.id} className="hairline py-1.5">
                  <div className="flex items-baseline gap-2">
                    <span className="num text-micro text-dim">#{record.source_row_index}</span>
                    <span className="border px-1 text-micro" style={{ borderColor: 'var(--color-warn)', color: 'var(--color-warn)' }}>
                      {ReasonCodeLabel[record.reason_code] ?? record.reason_code}
                    </span>
                    <span className="num flex-1 truncate text-micro text-dim">{record.reason_detail}</span>
                    <button
                      className="text-micro text-signal"
                      disabled={!canReplay || busy}
                      onClick={() => void replay([record.id])}
                    >
                      重放
                    </button>
                  </div>
                  <div className="num mt-0.5 truncate text-micro text-dim">{JSON.stringify(record.raw_payload)}</div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <section className="px-4 py-3">
        <div className="label-caps mb-2">映射快照（本次运行使用）</div>
        <div className="text-micro text-dim">
          {run.pipeline?.conflict_strategy} · 冲突键 {run.pipeline?.conflict_key ?? '—'} · 水位线列{' '}
          {run.pipeline?.watermark_column ?? '—'}
        </div>
        {run.mappings.slice(0, 12).map((mapping, index) => (
          <MappingRowEditor
            key={`${mapping.target_column}-${index}`}
            index={index}
            mapping={mapping}
            sourceFields={[mapping.source_field]}
            targetColumns={[mapping.target_column]}
            onChange={() => undefined}
            onRemove={() => undefined}
            onMove={() => undefined}
            readOnly
          />
        ))}
      </section>
    </div>
  );
};
