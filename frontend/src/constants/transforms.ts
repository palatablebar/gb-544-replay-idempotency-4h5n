import type { TransformType as TransformTypeValue } from '../types/models';

export const TransformType = {
  TRIM: 'trim',
  UPPER: 'upper',
  LOWER: 'lower',
  DATE_FORMAT: 'date_format',
  NUMBER_CAST: 'number_cast',
  CONCAT: 'concat',
  DEFAULT: 'default',
} as const;

export interface TransformParamSpec {
  key: string;
  label: string;
  required: boolean;
  placeholder: string;
  kind: 'text' | 'number' | 'list';
}

export const TransformLabel: Record<TransformTypeValue, string> = {
  trim: '去空格',
  upper: '转大写',
  lower: '转小写',
  date_format: '日期格式化',
  number_cast: '数值转换',
  concat: '字段拼接',
  default: '默认值填充',
};

export const TransformParamSpecs: Record<TransformTypeValue, TransformParamSpec[]> = {
  trim: [],
  upper: [],
  lower: [],
  date_format: [
    { key: 'from', label: '源格式', required: true, placeholder: '%Y/%m/%d', kind: 'text' },
    { key: 'to', label: '目标格式', required: true, placeholder: '%Y-%m-%d', kind: 'text' },
  ],
  number_cast: [
    { key: 'decimal_places', label: '小数位', required: false, placeholder: '2', kind: 'number' },
    { key: 'strip', label: '剔除字符', required: false, placeholder: '¥,元, ', kind: 'text' },
  ],
  concat: [
    { key: 'fields', label: '拼接字段', required: true, placeholder: 'store_no,sku', kind: 'list' },
    { key: 'separator', label: '分隔符', required: false, placeholder: '-', kind: 'text' },
  ],
  default: [{ key: 'value', label: '默认值', required: false, placeholder: '未知', kind: 'text' }],
};
