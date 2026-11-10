import type { ReactNode } from 'react';

interface Props {
  title: string;
  children: ReactNode;
  hint?: string;
  width?: number;
}

/** 右侧 300px 检查器：靠走线与左栏分隔，不做卡片 */
export const InspectorPanel = ({ title, children, hint, width = 300 }: Props) => (
  <aside
    className="shrink-0 overflow-y-auto border-l px-3 py-3"
    style={{ borderColor: 'var(--color-wire)', width }}
  >
    <div className="label-caps mb-2">{title}</div>
    {hint && <p className="mb-3 text-micro leading-5 text-dim">{hint}</p>}
    {children}
  </aside>
);
