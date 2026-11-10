import type { SourceType as SourceTypeValue } from '../types/models';

export const SourceType = {
  CSV: 'csv',
  JSONL: 'jsonl',
  POSTGRES_TABLE: 'postgres_table',
  MOCK_REST: 'mock_rest',
} as const;

export interface SourceTypeMeta {
  label: string;
  short: string;
  glyph: string;
  accent: string;
  configFields: { key: string; label: string; placeholder: string; kind: 'text' | 'number' | 'switch' }[];
  sampleHint: string;
}

export const SourceTypeMeta: Record<SourceTypeValue, SourceTypeMeta> = {
  csv: {
    label: 'CSV 文件',
    short: 'CSV',
    glyph: 'C',
    accent: 'var(--color-ok)',
    configFields: [
      { key: 'upload_path', label: '文件路径', placeholder: '/data/sources/store_sales_20261109.csv', kind: 'text' },
      { key: 'delimiter', label: '分隔符', placeholder: ',', kind: 'text' },
      { key: 'encoding', label: '编码', placeholder: 'utf-8', kind: 'text' },
      { key: 'has_header', label: '首行是表头', placeholder: 'true', kind: 'switch' },
    ],
    sampleHint: '按分隔符与编码解析，前 20 行作为样本',
  },
  jsonl: {
    label: 'JSONL 日志',
    short: 'JSONL',
    glyph: 'J',
    accent: 'var(--color-warn)',
    configFields: [
      { key: 'upload_path', label: '文件路径', placeholder: '/data/sources/member_profile_20261109.jsonl', kind: 'text' },
      { key: 'encoding', label: '编码', placeholder: 'utf-8', kind: 'text' },
    ],
    sampleHint: '每行一个 JSON 对象，字段清单取键并集',
  },
  postgres_table: {
    label: 'PostgreSQL 表',
    short: 'PG',
    glyph: 'P',
    accent: 'var(--color-signal)',
    configFields: [
      { key: 'dsn_alias', label: 'DSN 别名', placeholder: 'default', kind: 'text' },
      { key: 'schema', label: 'schema', placeholder: 'target', kind: 'text' },
      { key: 'table', label: '表名', placeholder: 'members_source', kind: 'text' },
    ],
    sampleHint: '同一实例，免第四个 schema；探测直接读列与行数',
  },
  mock_rest: {
    label: 'Mock REST 接口',
    short: 'REST',
    glyph: 'R',
    accent: 'var(--color-dim)',
    configFields: [
      { key: 'endpoint', label: '端点', placeholder: '/api/mock/rest/shop_orders', kind: 'text' },
      { key: 'page_size', label: '每页条数', placeholder: '50', kind: 'number' },
      { key: 'cursor_field', label: '水位线游标列', placeholder: 'order_id', kind: 'text' },
    ],
    sampleHint: '内置分页、限流与偶发 5xx，用于验证重试链路',
  },
};
