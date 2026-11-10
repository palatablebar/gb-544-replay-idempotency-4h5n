import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { mappingApi } from '../api/mapping';
import { pipelineApi } from '../api/pipeline';
import { sourceApi } from '../api/source';
import { MappingRowEditor } from '../components/common/MappingRowEditor';
import { SampleDataGrid } from '../components/common/SampleDataGrid';
import { useMappingDraft } from '../hooks/useMappingDraft';
import { useAuthStore } from '../stores/authStore';
import { useMappingStore } from '../stores/mappingStore';
import { SyncModeLabel } from '../constants/sync';
import { toHumanMessage } from '../utils/errorMessage';
import type { FieldMapping } from '../types/models';

const EMPTY_MAPPINGS: FieldMapping[] = [];

export const MappingEditorPage = () => {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const canWrite = useAuthStore((state) => state.can)('mappings:write');
  const setPreviewStore = useMappingStore((state) => state.setPreview);
  const markDirty = useMappingStore((state) => state.markDirty);

  const pipelineQuery = useQuery({ queryKey: ['pipeline', id], queryFn: () => pipelineApi.get(id) });
  const mappingQuery = useQuery({ queryKey: ['mappings', id], queryFn: () => mappingApi.list(id) });

  const initial = useMemo<FieldMapping[]>(
    () => mappingQuery.data?.items ?? EMPTY_MAPPINGS,
    [mappingQuery.data],
  );
  const draft = useMappingDraft(initial);
  const [sourceFields, setSourceFields] = useState<string[]>([]);
  const [preview, setPreview] = useState<{ before: Record<string, unknown>; after: Record<string, unknown> }[]>([]);
  const [previewErrors, setPreviewErrors] = useState<string[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const pipeline = pipelineQuery.data;
  const targetColumns = mappingQuery.data?.target_columns ?? [];

  useEffect(() => {
    markDirty(draft.dirty);
  }, [draft.dirty, markDirty]);

  useEffect(() => {
    if (!pipeline?.source_id) return;
    void sourceApi
      .get(pipeline.source_id)
      .then((source) => setSourceFields(source.probe_result?.columns ?? []))
      .catch(() => setSourceFields([]));
  }, [pipeline?.source_id]);

  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (draft.dirty) {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [draft.dirty]);

  const runPreview = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await mappingApi.preview(id, draft.toPayload(), 20);
      setPreview(result.samples);
      setPreviewErrors(result.failures.map((failure) => failure.reason_detail));
      setPreviewStore(result);
      setNotice(`试运行 ${result.samples.length} 行，拒绝 ${result.failures.length} 条`);
    } catch (err) {
      setError(toHumanMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (!draft.validate()) {
      setError('映射校验未通过：请处理内联报错后再保存');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await mappingApi.save(id, draft.toPayload());
      await queryClient.invalidateQueries({ queryKey: ['mappings', id] });
      await queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      draft.reset(draft.toPayload());
      setNotice('映射已保存，下一次运行按新规则转换');
    } catch (err) {
      setError(toHumanMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const fill = async () => {
    setBusy(true);
    try {
      const result = await mappingApi.fill(id);
      draft.reset(result.items);
      setNotice('已按源字段清单一键填充');
    } finally {
      setBusy(false);
    }
  };

  const leaveTo = (path: string) => {
    if (draft.dirty && !window.confirm('映射还有未保存的改动，确认离开？')) return;
    navigate(path);
  };

  const previewColumns = pipeline?.target_schema ? targetColumns : [];

  return (
    <div className="min-h-[calc(100vh-45px)]">
      <div className="flex flex-wrap items-center gap-3 border-b px-4 py-2" style={{ borderColor: 'var(--color-wire)' }}>
        <button className="text-micro text-dim hover:text-signal" onClick={() => leaveTo('/pipelines')}>
          ← 管道清单
        </button>
        <div className="title-font text-lead text-ink">{pipeline?.name ?? '映射编辑器'}</div>
        <div className="num text-micro text-dim">
          {pipeline?.target_full_name} · {SyncModeLabel[pipeline?.sync_mode ?? 'incremental']} · 水位线{' '}
          <span style={{ color: 'var(--color-signal)' }}>{pipeline?.watermark_column ?? '—'}</span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {draft.dirty && <span className="text-micro" style={{ color: 'var(--color-warn)' }}>未保存</span>}
          <button
            className="border px-2 py-1 text-micro"
            style={{ borderColor: 'var(--color-wire)', color: 'var(--color-dim)' }}
            onClick={() => void fill()}
            disabled={!canWrite || busy}
          >
            从源字段填充
          </button>
          <button
            className="border px-2 py-1 text-micro"
            style={{ borderColor: 'var(--color-wire)', color: 'var(--color-ink)' }}
            onClick={() => void runPreview()}
            disabled={busy}
          >
            试运行 20 行
          </button>
          <button
            className="border px-2 py-1 text-micro"
            style={{ borderColor: 'var(--color-signal)', color: 'var(--color-signal)' }}
            onClick={() => void save()}
            disabled={!canWrite || busy}
          >
            保存映射
          </button>
        </div>
      </div>

      {(notice || error) && (
        <div className="border-b px-4 py-1.5 text-micro" style={{ borderColor: 'var(--color-wire)' }}>
          {error ? <span style={{ color: 'var(--color-danger)' }}>{error}</span> : <span className="text-dim">{notice}</span>}
        </div>
      )}

      {/* 左右双列字段面板 + 下方样本区；映射行是带编号的密集行，不做卡片 */}
      <div className="grid grid-cols-1 gap-0 lg:grid-cols-[1fr_1fr]">
        <div className="border-b border-r px-4 py-3" style={{ borderColor: 'var(--color-wire)' }}>
          <div className="label-caps mb-2">源字段 · {sourceFields.length}</div>
          <div className="flex flex-wrap gap-1">
            {sourceFields.length === 0 && <span className="text-dense text-dim">尚未探测源字段，去 /sources 点『探测』</span>}
            {sourceFields.map((field) => {
              const used = draft.draft.some((row) => row.source_field === field);
              return (
                <button
                  key={field}
                  className="num border px-1.5 text-micro"
                  style={{
                    borderColor: used ? 'var(--color-signal)' : 'var(--color-wire)',
                    color: used ? 'var(--color-signal)' : 'var(--color-dim)',
                  }}
                  onClick={() => {
                    if (!canWrite) return;
                    draft.addRow();
                    draft.updateRow(draft.draft.length, { source_field: field });
                  }}
                >
                  {field}
                </button>
              );
            })}
          </div>
        </div>
        <div className="border-b px-4 py-3" style={{ borderColor: 'var(--color-wire)' }}>
          <div className="label-caps mb-2">目标列 · {targetColumns.length}</div>
          <div className="flex flex-wrap gap-1">
            {targetColumns.map((column) => {
              const used = draft.draft.some((row) => row.target_column === column);
              return (
                <span
                  key={column}
                  className="num border px-1.5 text-micro"
                  style={{
                    borderColor: used ? 'var(--color-ok)' : 'var(--color-wire)',
                    color: used ? 'var(--color-ok)' : 'var(--color-dim)',
                  }}
                >
                  {column}
                </span>
              );
            })}
          </div>
        </div>
      </div>

      <div className="px-4 py-3">
        <div className="mb-1 flex items-center gap-2">
          <div className="label-caps">映射行 · {draft.draft.length}</div>
          {canWrite && (
            <button className="text-micro text-signal" onClick={draft.addRow}>
              + 新增一行
            </button>
          )}
        </div>
        {draft.draft.length === 0 ? (
          <p className="text-dense text-dim">还没有映射行。点『从源字段填充』或右上角新增一行。</p>
        ) : (
          draft.draft.map((row, index) => (
            <MappingRowEditor
              key={`${row.id ?? 'new'}-${index}`}
              index={index}
              mapping={row as FieldMapping}
              sourceFields={sourceFields}
              targetColumns={targetColumns}
              error={draft.errors[index]}
              readOnly={!canWrite}
              onChange={(patch) => draft.updateRow(index, patch)}
              onRemove={() => draft.removeRow(index)}
              onMove={(direction) => draft.moveRow(index, direction)}
            />
          ))
        )}
      </div>

      <div className="border-t px-4 py-3" style={{ borderColor: 'var(--color-wire)' }}>
        <div className="mb-2 flex items-center gap-3">
          <div className="label-caps">样本预览 · before / after</div>
          {previewErrors.length > 0 && (
            <span className="text-micro" style={{ color: 'var(--color-danger)' }}>
              {previewErrors.length} 条转换失败：{previewErrors[0]}
            </span>
          )}
        </div>
        {preview.length === 0 ? (
          <p className="text-dense text-dim">点右上角『试运行 20 行』，这里会显示每列映射前后的值。</p>
        ) : (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div>
              <div className="label-caps mb-1">before · 源行</div>
              <SampleDataGrid columns={previewColumns} rows={preview.map((item) => item.before)} />
            </div>
            <div>
              <div className="label-caps mb-1">after · 转换后</div>
              <SampleDataGrid columns={previewColumns} rows={preview.map((item) => item.after)} />
            </div>
          </div>
        )}
      </div>

      <div className="hairline px-4 py-2 text-micro text-dim">
        水位线提示：本管道按 <span style={{ color: 'var(--color-signal)' }}>{pipeline?.watermark_column ?? '—'}</span> 做增量比较，
        保存映射后只影响后续运行。{' '}
        <Link to="/runs" className="text-signal">
          去看运行时间线
        </Link>
      </div>
    </div>
  );
};
