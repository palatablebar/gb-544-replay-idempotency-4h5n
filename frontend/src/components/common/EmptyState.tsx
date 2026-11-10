import type { ReactNode } from 'react';

interface Props {
  label: string;
  description: string;
  action?: ReactNode;
}

/** 教学式空态文字，不放大图标、不做居中大图 */
export const EmptyState = ({ label, description, action }: Props) => (
  <div className="px-4 py-8">
    <div className="label-caps mb-2">{label}</div>
    <p className="max-w-[520px] text-dense leading-6 text-dim">{description}</p>
    {action && <div className="mt-4">{action}</div>}
  </div>
);
