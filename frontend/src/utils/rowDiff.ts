export type DiffKind = 'missing' | 'extra' | 'type_changed' | 'value_changed';

export interface CellDiff {
  column: string;
  source: unknown;
  target: unknown;
  kind: DiffKind;
}

/** 归一化：时间戳的 T/时区差异、12.50 与 12.5 的数字写法差异不算差异 */
const normalize = (value: unknown): string => {
  if (value === null || value === undefined) return '';
  if (typeof value === 'number') return String(value);
  let text = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}T/.test(text)) {
    text = text.replace('T', ' ').replace(/(\.\d+)?(Z|[+-]\d{2}:\d{2})$/, '').slice(0, 19);
  }
  if (/^-?\d+(\.\d+)?$/.test(text)) {
    const numeric = Number(text);
    if (!Number.isNaN(numeric)) return String(numeric);
  }
  return text;
};

const typeOf = (value: unknown): string => {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'number') return 'number';
  if (typeof value === 'boolean') return 'boolean';
  const text = String(value);
  if (/^-?\d+(\.\d+)?$/.test(text)) return 'number';
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return 'date';
  return 'string';
};

/** 两行列级 diff：missing / extra / type_changed / value_changed */
export const diffRows = (
  sourceRow: Record<string, unknown>,
  targetRow: Record<string, unknown>,
  columns?: string[],
): CellDiff[] => {
  const keys = columns ?? Array.from(new Set([...Object.keys(sourceRow), ...Object.keys(targetRow)]));
  const diffs: CellDiff[] = [];
  for (const column of keys) {
    const source = sourceRow[column];
    const target = targetRow[column];
    if (source === undefined && target === undefined) continue;
    if (source === undefined) {
      diffs.push({ column, source, target, kind: 'extra' });
      continue;
    }
    if (target === undefined) {
      diffs.push({ column, source, target, kind: 'missing' });
      continue;
    }
    if (normalize(source) === normalize(target)) continue;
    const kind: DiffKind = typeOf(source) !== typeOf(target) ? 'type_changed' : 'value_changed';
    diffs.push({ column, source, target, kind });
  }
  return diffs;
};

export const onlyDiffs = (diffs: CellDiff[], columnsToCheck: string[]): Set<string> =>
  new Set(diffs.filter((diff) => columnsToCheck.includes(diff.column)).map((diff) => diff.column));
