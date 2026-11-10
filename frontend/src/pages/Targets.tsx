import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { targetApi } from '../api/target';
import { SampleDataGrid } from '../components/common/SampleDataGrid';
import { EmptyState } from '../components/common/EmptyState';
import { useAuthStore } from '../stores/authStore';
import { formatCount } from '../utils/formatCount';
import { toHumanMessage } from '../utils/errorMessage';

export const TargetsPage = () => {
  const role = useAuthStore((state) => state.user?.role);
  const tablesQuery = useQuery({ queryKey: ['targets'], queryFn: () => targetApi.list() });
  const tables = tablesQuery.data?.items ?? [];
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const current = tables.find((table) => table.full_name === selected) ?? tables[0];

  useEffect(() => {
    if (!selected && tables.length) setSelected(tables[0].full_name);
  }, [selected, tables]);

  const rowsQuery = useQuery({
    queryKey: ['target-rows', current?.full_name, page, query],
    queryFn: () =>
      targetApi
        .browse(current!.schema, current!.table, { page, page_size: 20, q: query || undefined })
        .catch((err) => {
          setError(toHumanMessage(err));
          throw err;
        }),
    enabled: Boolean(current),
  });

  const totalPages = current ? Math.max(Math.ceil((rowsQuery.data?.total ?? 0) / 20), 1) : 1;

  return (
    <div className="flex min-h-[calc(100vh-45px)]">
      <aside className="w-[240px] shrink-0 overflow-y-auto border-r" style={{ borderColor: 'var(--color-wire)' }}>
        <div className="label-caps px-3 py-2">target schema · {tables.length}</div>
        {tables.map((table) => (
          <button
            key={table.full_name}
            className="block w-full border-l-2 px-3 py-1.5 text-left"
            style={{
              borderColor: current?.full_name === table.full_name ? 'var(--color-signal)' : 'transparent',
              backgroundColor: current?.full_name === table.full_name ? 'var(--color-select)' : 'transparent',
            }}
            onClick={() => {
              setSelected(table.full_name);
              setPage(1);
              setQuery('');
            }}
          >
            <div className="num text-dense text-ink">{table.table}</div>
            <div className="num text-micro text-dim">{formatCount(table.row_count)} 行</div>
            {table.pipeline_name && <div className="truncate text-micro text-dim">{table.pipeline_name}</div>}
          </button>
        ))}
      </aside>

      <section className="min-w-0 flex-1">
        {!current ? (
          <EmptyState label="目标表" description="还没有目标表，先建管道并跑一次同步。" />
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3 border-b px-4 py-2" style={{ borderColor: 'var(--color-wire)' }}>
              <div className="title-font text-lead text-ink">{current.full_name}</div>
              <div className="num text-micro text-dim">
                {formatCount(rowsQuery.data?.total ?? current.row_count)} 行 · {current.columns.length} 列
                {current.conflict_key && ` · 冲突键 ${current.conflict_key}`}
              </div>
              <div className="ml-auto flex items-center gap-2">
                <input
                  className="num w-[220px]"
                  placeholder={current.conflict_key ? `按 ${current.conflict_key} 搜索` : '搜索'}
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      setQuery(search);
                      setPage(1);
                    }
                  }}
                />
                <button
                  className="border px-2 py-1 text-micro"
                  style={{ borderColor: 'var(--color-signal)', color: 'var(--color-signal)' }}
                  onClick={() => {
                    setQuery(search);
                    setPage(1);
                  }}
                >
                  搜索
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 border-b px-4 py-1.5" style={{ borderColor: 'var(--color-wire)' }}>
              {current.columns.map((column) => (
                <span
                  key={column.name}
                  className="num text-micro"
                  style={{ color: column.is_audit ? 'var(--color-signal)' : 'var(--color-dim)' }}
                >
                  {column.name}
                  <span className="ml-1" style={{ color: 'var(--color-wire)' }}>
                    {column.type}
                  </span>
                </span>
              ))}
            </div>

            {error && <div className="px-4 py-2 text-dense" style={{ color: 'var(--color-danger)' }}>{error}</div>}

            <div className="px-4 py-2">
              <SampleDataGrid
                columns={(rowsQuery.data?.rows?.[0] ? Object.keys(rowsQuery.data.rows[0]) : current.columns.map((column) => column.name))}
                rows={rowsQuery.data?.rows ?? []}
                emptyHint="没有匹配的行；试试清空搜索条件"
              />
            </div>

            <div className="flex items-center gap-3 border-t px-4 py-2 text-micro text-dim" style={{ borderColor: 'var(--color-wire)' }}>
              <button disabled={page <= 1} onClick={() => setPage((value) => Math.max(value - 1, 1))} className="border px-2" style={{ borderColor: 'var(--color-wire)' }}>
                上一页
              </button>
              <span className="num">
                {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((value) => value + 1)}
                className="border px-2"
                style={{ borderColor: 'var(--color-wire)' }}
              >
                下一页
              </button>
              <span className="ml-4">
                {role === 'viewer' ? 'BI 只读：可溯源 _sync_run_id 与 _synced_at' : '写入时记录 _sync_run_id / _synced_at'}
              </span>
              {current.pipeline_id && (
                <Link to="/runs" className="ml-auto text-signal">
                  去看运行时间线
                </Link>
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
};
