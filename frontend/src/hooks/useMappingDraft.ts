import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FieldMapping } from '../types/models';

const blankMapping = (index: number): FieldMapping => ({
  source_field: '',
  target_column: '',
  transform_type: 'trim',
  transform_config: {},
  default_value: null,
  is_required: false,
  order_index: index,
});

/** FieldMapping[] 本地草稿：增删排序 + dirty + validate + toPayload */
export const useMappingDraft = (initial: FieldMapping[]) => {
  const [draft, setDraft] = useState<FieldMapping[]>(initial);
  const [baseline, setBaseline] = useState<string>(JSON.stringify(initial));
  const [errors, setErrors] = useState<Record<number, string>>({});

  useEffect(() => {
    // 只在数据真正变化时重置草稿：`initial` 每次渲染可能是新的空数组引用
    const next = JSON.stringify(initial);
    setBaseline((prev) => (prev === next ? prev : next));
    setDraft((current) => (JSON.stringify(current) === next ? current : initial));
  }, [initial]);

  const dirty = useMemo(() => JSON.stringify(draft) !== baseline, [draft, baseline]);

  const addRow = useCallback(() => {
    setDraft((current) => [...current, blankMapping(current.length)]);
  }, []);

  const removeRow = useCallback((index: number) => {
    setDraft((current) => current.filter((_, position) => position !== index));
  }, []);

  const updateRow = useCallback((index: number, patch: Partial<FieldMapping>) => {
    setDraft((current) =>
      current.map((row, position) => (position === index ? { ...row, ...patch } : row)),
    );
  }, []);

  const moveRow = useCallback((index: number, direction: -1 | 1) => {
    setDraft((current) => {
      const target = index + direction;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next.map((row, position) => ({ ...row, order_index: position }));
    });
  }, []);

  const validate = useCallback(() => {
    const nextErrors: Record<number, string> = {};
    const seen = new Set<string>();
    draft.forEach((row, index) => {
      if (!row.target_column.trim()) nextErrors[index] = '目标列不能为空';
      else if (seen.has(row.target_column)) nextErrors[index] = '目标列重复';
      else if (!row.source_field.trim()) nextErrors[index] = '源字段不能为空';
      seen.add(row.target_column);
    });
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0 && draft.length > 0;
  }, [draft]);

  const toPayload = useCallback(
    (): FieldMapping[] =>
      draft.map((row, index) => ({
        ...row,
        order_index: index,
        transform_config: row.transform_config ?? {},
      })),
    [draft],
  );

  const reset = useCallback((next: FieldMapping[]) => {
    setDraft(next);
    setBaseline(JSON.stringify(next));
    setErrors({});
  }, []);

  return { draft, dirty, errors, addRow, removeRow, updateRow, moveRow, validate, toPayload, reset };
};
