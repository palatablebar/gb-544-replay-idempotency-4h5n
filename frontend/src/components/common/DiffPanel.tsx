import { diffRows, onlyDiffs } from '../../utils/rowDiff';
import type { FieldMapping } from '../../types/models';

interface Props {
  sourceRow: Record<string, unknown>;
  targetRow: Record<string, unknown>;
  mappings: FieldMapping[];
  showOnlyDiff?: boolean;
}

/** 源值与落库值并排对比，按列高亮差异 */
export const DiffPanel = ({ sourceRow, targetRow, mappings, showOnlyDiff }: Props) => {
  const columns = mappings.map((mapping) => mapping.target_column);
  const diffs = diffRows(sourceRow, targetRow);
  const changed = onlyDiffs(diffs, [...columns, ...mappings.map((mapping) => mapping.source_field)]);
  const rows = mappings.filter((mapping) => (showOnlyDiff ? changed.has(mapping.target_column) : true));

  if (!rows.length) {
    return <div className="px-2 py-3 text-dense text-dim">这一行源值与落库值逐列一致</div>;
  }

  return (
    <table className="grid-table">
      <thead>
        <tr>
          <th style={{ width: 150 }}>目标列</th>
          <th>源值</th>
          <th>落库值</th>
          <th style={{ width: 110 }}>差异</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((mapping) => {
          const source = sourceRow[mapping.source_field];
          const target = targetRow[mapping.target_column];
          const isDiff = changed.has(mapping.target_column) || changed.has(mapping.source_field);
          const kind = diffs.find((diff) => diff.column === mapping.target_column)?.kind;
          return (
            <tr key={mapping.target_column}>
              <td className="text-dense text-dim">{mapping.target_column}</td>
              <td className={`num ${isDiff ? 'diff-changed' : ''}`}>
                {source === undefined || source === null || source === '' ? <span className="null-cell">∅</span> : String(source)}
              </td>
              <td className={`num ${isDiff ? 'diff-changed' : ''}`}>
                {target === undefined || target === null || target === '' ? <span className="null-cell">∅</span> : String(target)}
              </td>
              <td className="text-micro" style={{ color: isDiff ? 'var(--color-warn)' : 'var(--color-dim)' }}>
                {isDiff ? kind ?? 'value_changed' : '一致'}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
};
