import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { sourceApi } from '../api/source';
import { SampleDataGrid } from '../components/common/SampleDataGrid';
import { SourceBadge } from '../components/common/SourceBadge';
import { EmptyState } from '../components/common/EmptyState';
import { useSourceProbe } from '../hooks/useSourceProbe';
import { useAuthStore } from '../stores/authStore';
import { useSourceStore } from '../stores/sourceStore';
import { SourceTypeMeta } from '../constants/sources';
import type { DataSource, SourceType } from '../types/models';
import { formatTimestamp } from '../utils/formatCount';
import { toHumanMessage, errorHint } from '../utils/errorMessage';

export const SourcesPage = () => {
  const queryClient = useQueryClient();
  const canWrite = useAuthStore((state) => state.can)('sources:write');
  const selectedId = useSourceStore((state) => state.selectedSourceId);
  const select = useSourceStore((state) => state.select);
  const probe = useSourceProbe();
  const [sample, setSample] = useState<{ columns: string[]; rows: Record<string, unknown>[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data } = useQuery({ queryKey: ['sources'], queryFn: () => sourceApi.list() });
  const sources = data?.items ?? [];
  const selected: DataSource | undefined = sources.find((item) => item.id === selectedId) ?? sources[0];

  useEffect(() => {
    if (!selectedId && sources.length) select(sources[0].id);
  }, [selectedId, sources, select]);

  const loadSample = async (source: DataSource) => {
    setError(null);
    try {
      const payload = await sourceApi.sample(source.id);
      setSample({ columns: payload.columns, rows: payload.rows });
    } catch (err) {
      setError(toHumanMessage(err));
    }
  };

  const runProbe = async (source: DataSource) => {
    setError(null);
    try {
      await probe.mutateAsync(source.id);
      await loadSample(source);
    } catch (err) {
      setError(toHumanMessage(err));
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-45px)]">
      <section className="flex-1 border-r" style={{ borderColor: 'var(--color-wire)' }}>
        <div className="flex items-center justify-between px-4 py-2">
          <div>
            <div className="label-caps">数据源登记台</div>
            <div className="num text-dense text-dim">
              {sources.length} 个源 · 被 {sources.reduce((sum, item) => sum + item.referenced_pipelines.length, 0)} 条管道引用
            </div>
          </div>
          <span className="text-micro text-dim">{canWrite ? 'owner 可登记 / 探测 / 删除' : '只读角色'}</span>
        </div>

        {sources.length === 0 ? (
          <EmptyState
            label="还没有数据源"
            description="先登记一个源：CSV 直接拖入，PostgreSQL 填 schema + 表名，Mock REST 用内置示例地址；登记后可以点『探测』看字段"
          />
        ) : (
          <table className="grid-table">
            <thead>
              <tr>
                <th>源</th>
                <th style={{ width: 130 }}>类型</th>
                <th style={{ width: 100 }}>字段数</th>
                <th style={{ width: 160 }}>最近探测</th>
                <th style={{ width: 170 }}>被引用</th>
                <th style={{ width: 130 }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source, index) => (
                <tr
                  key={source.id}
                  className="stagger-row cursor-pointer"
                  style={{
                    animationDelay: `${index * 18}ms`,
                    backgroundColor: selected?.id === source.id ? 'var(--color-select)' : 'transparent',
                  }}
                  onClick={() => {
                    select(source.id);
                    setSample(null);
                  }}
                >
                  <td>
                    <span className="text-dense text-ink">{source.name}</span>
                  </td>
                  <td>
                    <SourceBadge type={source.source_type} status={source.status} lastProbedAt={source.last_probed_at} />
                  </td>
                  <td className="num text-dense text-dim">{source.probe_result?.columns?.length ?? 0}</td>
                  <td className="num text-micro text-dim">{formatTimestamp(source.last_probed_at)}</td>
                  <td className="text-micro text-dim">
                    {source.referenced_pipelines.length
                      ? source.referenced_pipelines.map((ref) => ref.name).join('、')
                      : '未被引用'}
                  </td>
                  <td>
                    <button
                      className="text-micro text-signal"
                      onClick={(event) => {
                        event.stopPropagation();
                        void runProbe(source);
                      }}
                    >
                      {probe.isPending && probe.variables === source.id ? '探测中…' : '探测'}
                    </button>
                    <button
                      className="ml-3 text-micro text-dim"
                      onClick={(event) => {
                        event.stopPropagation();
                        select(source.id);
                        void loadSample(source);
                      }}
                    >
                      抽样
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {error && (
          <div className="mx-4 mt-3 border px-3 py-2 text-dense" style={{ borderColor: 'var(--color-danger)', color: 'var(--color-danger)' }}>
            {error}
            <div className="mt-1 text-micro text-dim">{errorHint(error)}</div>
            {selected && (
              <button className="mt-2 text-micro text-signal" onClick={() => void runProbe(selected)}>
                重试探测
              </button>
            )}
          </div>
        )}
      </section>

      <aside className="w-[420px] shrink-0 overflow-y-auto px-3 py-3">
        <div className="label-caps mb-2">探测结果 · 前 20 行样本</div>
        {selected ? (
          <>
            <div className="mb-3 space-y-1 text-dense text-dim">
              <div>
                <span className="label-caps">配置</span>
                <div className="num mt-1 break-all text-micro">{JSON.stringify(selected.config)}</div>
              </div>
              <div className="text-micro">
                {SourceTypeMeta[selected.source_type as SourceType]?.sampleHint}
              </div>
              {selected.probe_result?.note && (
                <div className="text-micro" style={{ color: 'var(--color-signal)' }}>
                  {selected.probe_result.note}
                </div>
              )}
              {selected.probe_result?.columns && (
                <div className="mt-2">
                  <span className="label-caps">字段清单</span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {selected.probe_result.columns.map((column) => (
                      <span key={column} className="num border px-1.5 text-micro" style={{ borderColor: 'var(--color-wire)' }}>
                        {column}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <button
              className="mb-2 text-micro text-signal"
              onClick={() => {
                void loadSample(selected);
                queryClient.invalidateQueries({ queryKey: ['sources'] });
              }}
            >
              拉取样本
            </button>
            {sample && (
              <SampleDataGrid columns={sample.columns} rows={sample.rows} emptyHint="该源没有可显示样本" />
            )}
          </>
        ) : (
          <div className="text-dense text-dim">选择左侧任意一个源查看探测结果</div>
        )}
      </aside>
    </div>
  );
};
