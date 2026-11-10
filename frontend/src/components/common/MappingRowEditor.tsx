import type { FieldMapping, TransformType } from '../../types/models';
import { TransformLabel, TransformParamSpecs } from '../../constants/transforms';

interface Props {
  index: number;
  mapping: FieldMapping;
  sourceFields: string[];
  targetColumns: string[];
  error?: string;
  onChange: (patch: Partial<FieldMapping>) => void;
  onRemove: () => void;
  onMove: (direction: -1 | 1) => void;
  readOnly?: boolean;
}

/** 单条字段映射编辑行：源字段 / 目标列 / 转换类型 / 参数 / 必填 / 删除，带内联校验 */
export const MappingRowEditor = ({
  index,
  mapping,
  sourceFields,
  targetColumns,
  error,
  onChange,
  onRemove,
  onMove,
  readOnly,
}: Props) => {
  const specs = TransformParamSpecs[mapping.transform_type] ?? [];
  const config = (mapping.transform_config ?? {}) as Record<string, unknown>;

  const setParam = (key: string, raw: string, kind: 'text' | 'number' | 'list') => {
    let value: unknown = raw;
    if (kind === 'number') value = raw === '' ? undefined : Number(raw);
    if (kind === 'list') value = raw.split(',').map((item) => item.trim()).filter(Boolean);
    onChange({ transform_config: { ...config, [key]: value } });
  };

  return (
    <div className="hairline py-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="num w-7 text-micro text-dim">{String(index + 1).padStart(2, '0')}</span>
        <select
          className="w-[150px]"
          value={mapping.source_field}
          disabled={readOnly}
          onChange={(event) => onChange({ source_field: event.target.value })}
        >
          <option value="">选择源字段</option>
          {sourceFields.map((field) => (
            <option key={field} value={field}>
              {field}
            </option>
          ))}
          {!sourceFields.includes(mapping.source_field) && mapping.source_field && (
            <option value={mapping.source_field}>{mapping.source_field}</option>
          )}
        </select>
        <span className="text-dim">→</span>
        <input
          className="w-[150px]"
          value={mapping.target_column}
          disabled={readOnly}
          placeholder="目标列"
          list="syncmesh-target-columns"
          onChange={(event) => onChange({ target_column: event.target.value })}
        />
        <select
          className="w-[130px]"
          value={mapping.transform_type}
          disabled={readOnly}
          onChange={(event) =>
            onChange({ transform_type: event.target.value as TransformType, transform_config: {} })
          }
        >
          {Object.entries(TransformLabel).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        {specs.map((spec) => (
          <label key={spec.key} className="flex items-center gap-1 text-micro text-dim">
            {spec.label}
            <input
              className="w-[110px]"
              disabled={readOnly}
              placeholder={spec.placeholder}
              value={
                spec.kind === 'list'
                  ? Array.isArray(config[spec.key])
                    ? (config[spec.key] as string[]).join(',')
                    : ''
                  : String(config[spec.key] ?? '')
              }
              onChange={(event) => setParam(spec.key, event.target.value, spec.kind)}
            />
          </label>
        ))}
        <label className="flex items-center gap-1 text-micro text-dim">
          <input
            type="checkbox"
            className="h-3 w-3"
            checked={mapping.is_required}
            disabled={readOnly}
            onChange={(event) => onChange({ is_required: event.target.checked })}
          />
          必填
        </label>
        {!readOnly && (
          <span className="ml-auto flex items-center gap-1">
            <button className="text-micro text-dim hover:text-signal" onClick={() => onMove(-1)} type="button">
              ↑
            </button>
            <button className="text-micro text-dim hover:text-signal" onClick={() => onMove(1)} type="button">
              ↓
            </button>
            <button className="text-micro text-dim hover:text-danger" onClick={onRemove} type="button">
              删除
            </button>
          </span>
        )}
      </div>
      {error && <div className="mt-1 pl-9 text-micro" style={{ color: 'var(--color-danger)' }}>{error}</div>}
      {mapping.target_column && targetColumns.length > 0 && !targetColumns.includes(mapping.target_column) && (
        <div className="mt-1 pl-9 text-micro" style={{ color: 'var(--color-warn)' }}>
          目标表没有列 {mapping.target_column}
        </div>
      )}
      <datalist id="syncmesh-target-columns">
        {targetColumns.map((column) => (
          <option key={column} value={column} />
        ))}
      </datalist>
    </div>
  );
};
