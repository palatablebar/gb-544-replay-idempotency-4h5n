import type { SyncRunBrief } from '../../types/models';
import { RunStatusPill } from '../common/RunStatusPill';
import { formatTimestamp } from '../../utils/formatCount';
import { isNoNewData, watermarkLine } from '../../utils/watermark';
import { TriggerLabel } from '../../constants/sync';

interface Props {
  runs: SyncRunBrief[];
  selectedId?: string | null;
  onSelect?: (id: string) => void;
}

/** 纵向时间线：左侧持续竖线、节点用小方块；行之间只有发丝分隔 */
export const RunTimeline = ({ runs, selectedId, onSelect }: Props) => (
  <div className="relative">
    <div className="absolute bottom-0 left-[7px] top-0 w-px" style={{ backgroundColor: 'var(--color-wire)' }} />
    {runs.map((run, index) => {
      const active = run.status === 'running';
      return (
        <button
          key={run.id}
          onClick={() => onSelect?.(run.id)}
          className="stagger-row relative flex w-full items-baseline gap-3 border-b py-2 pl-6 pr-3 text-left hover:bg-deck"
          style={{
            borderColor: 'var(--color-wire)',
            animationDelay: `${Math.min(index, 12) * 18}ms`,
            backgroundColor: selectedId === run.id ? 'var(--color-select)' : 'transparent',
          }}
        >
          <span
            className={`absolute left-0 top-[13px] inline-block h-2 w-2 ${active ? 'node-live' : ''}`}
            style={{ backgroundColor: active ? 'var(--color-signal)' : 'var(--color-wire)' }}
          />
          <span className="time-col num text-micro text-dim">{formatTimestamp(run.created_at)}</span>
          <span className="min-w-[140px] flex-1 truncate text-dense text-ink">{run.pipeline_name ?? run.pipeline_id}</span>
          <span className="text-micro text-dim">{TriggerLabel[run.trigger_type] ?? run.trigger_type}</span>
          <RunStatusPill
            status={run.status}
            rows={{ read: run.rows_read, written: run.rows_written, rejected: run.rows_rejected }}
          />
          <span className="num w-[70px] text-right text-micro text-dim">{run.duration_text}</span>
          <span className="num w-[190px] truncate text-right text-micro text-dim">
            {isNoNewData(run) ? '本批无新数据' : watermarkLine(run.watermark_from, run.watermark_value)}
          </span>
        </button>
      );
    })}
  </div>
);
