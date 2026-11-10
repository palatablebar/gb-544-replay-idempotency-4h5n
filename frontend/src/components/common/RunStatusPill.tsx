import type { RunStatus } from '../../types/models';
import { RunStatusLabel, RunStatusToken } from '../../constants/sync';
import { formatCount } from '../../utils/formatCount';

interface Props {
  status: RunStatus;
  rows?: { read: number; written: number; rejected: number };
  compact?: boolean;
}

/** 六态胶囊 + 行数三元组（读 / 写 / 拒） */
export const RunStatusPill = ({ status, rows, compact }: Props) => {
  const color = RunStatusToken[status] ?? 'var(--color-dim)';
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      <span
        className="inline-flex items-center gap-1.5 border px-1.5 py-[1px] text-micro font-semibold"
        style={{ borderColor: color, color, letterSpacing: '0.04em' }}
      >
        <span
          className={status === 'running' ? 'node-live inline-block h-1.5 w-1.5' : 'inline-block h-1.5 w-1.5'}
          style={{ backgroundColor: color }}
        />
        {RunStatusLabel[status] ?? status}
      </span>
      {!compact && rows && (
        <span className="num text-dense text-dim">
          {formatCount(rows.read)} / {formatCount(rows.written)} /{' '}
          <span style={{ color: rows.rejected > 0 ? 'var(--color-warn)' : 'var(--color-dim)' }}>
            {formatCount(rows.rejected)}
          </span>
        </span>
      )}
    </span>
  );
};
