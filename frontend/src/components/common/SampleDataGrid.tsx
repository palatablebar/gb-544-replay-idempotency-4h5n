import { useMemo, useState } from 'react';
import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from '@tanstack/react-table';
import type { SampleColumn } from '../../types/table';

interface Props {
  columns: SampleColumn[] | string[];
  rows: Record<string, unknown>[];
  diffColumns?: Set<string>;
  emptyHint?: string;
}

/** 只读样本表：null 显示 ∅、超长值截断可展开、带行号列、固定表头 */
export const SampleDataGrid = ({ columns, rows, diffColumns, emptyHint }: Props) => {
  const [expanded, setExpanded] = useState<string | null>(null);
  const normalized: SampleColumn[] = useMemo(
    () => (typeof columns[0] === 'string' ? (columns as string[]).map((key) => ({ key, header: key })) : (columns as SampleColumn[])),
    [columns],
  );

  const columnDefs = useMemo<ColumnDef<Record<string, unknown>>[]>(() => {
    const defs: ColumnDef<Record<string, unknown>>[] = [
      {
        id: '__index',
        header: '#',
        cell: ({ row }) => <span className="text-dim num">{row.index + 1}</span>,
        size: 42,
      },
    ];
    for (const column of normalized) {
      defs.push({
        id: column.key,
        accessorKey: column.key,
        header: column.header,
        cell: ({ getValue }) => {
          const value = getValue();
          if (value === null || value === undefined || value === '') {
            return <span className="null-cell">∅</span>;
          }
          const text = String(value);
          const isLong = text.length > 34;
          const changed = diffColumns?.has(column.key);
          const isExpanded = expanded === `${column.key}`;
          return (
            <span
              className={`num ${changed ? 'diff-changed' : ''}`}
              title={text}
              onClick={() => isLong && setExpanded(isExpanded ? null : column.key)}
              style={{ cursor: isLong ? 'pointer' : 'default' }}
            >
              {isLong && !isExpanded ? `${text.slice(0, 34)}…` : text}
            </span>
          );
        },
      });
    }
    return defs;
  }, [normalized, expanded, diffColumns]);

  const table = useReactTable({
    data: rows,
    columns: columnDefs,
    getCoreRowModel: getCoreRowModel(),
  });

  if (!rows.length) {
    return <div className="px-3 py-4 text-dense text-dim">{emptyHint ?? '没有可显示的样本行'}</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="grid-table">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id} style={{ width: header.getSize() }}>
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
