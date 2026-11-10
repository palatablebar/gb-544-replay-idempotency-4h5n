import type { SourceStatus, SourceType } from '../../types/models';
import { SourceTypeMeta } from '../../constants/sources';
import { formatTimestamp } from '../../utils/formatCount';

interface Props {
  type: SourceType;
  status?: SourceStatus;
  lastProbedAt?: string | null;
  name?: string;
}

const StatusDot = ({ status }: { status?: SourceStatus }) => {
  const color =
    status === 'ok' ? 'var(--color-ok)' : status === 'unreachable' ? 'var(--color-danger)' : 'var(--color-dim)';
  const label = status === 'ok' ? '连通' : status === 'unreachable' ? '不可达' : '未探测';
  return (
    <span className="inline-flex items-center gap-1 text-micro text-dim">
      <span className="inline-block h-1.5 w-1.5" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
};

/** 源类型徽标 + 连接状态点 + 悬停显示最近探测时间 */
export const SourceBadge = ({ type, status, lastProbedAt, name }: Props) => {
  const meta = SourceTypeMeta[type];
  return (
    <span className="inline-flex items-center gap-2" title={`${meta?.label ?? type} · 最近探测 ${formatTimestamp(lastProbedAt ?? null)}`}>
      <span
        className="inline-flex h-4 w-4 items-center justify-center border text-[10px] font-bold"
        style={{ borderColor: meta?.accent ?? 'var(--color-wire)', color: meta?.accent ?? 'var(--color-dim)' }}
      >
        {meta?.glyph ?? '?'}
      </span>
      {name && <span className="text-dense text-ink">{name}</span>}
      <StatusDot status={status} />
    </span>
  );
};
