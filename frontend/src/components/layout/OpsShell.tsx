import type { ReactNode } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { useQuotaStore } from '../../stores/quotaStore';

const NAV = [
  { to: '/sources', label: '源登记台' },
  { to: '/pipelines', label: '管道清单' },
  { to: '/runs', label: '运行时间线' },
  { to: '/targets', label: '目标表' },
];

/** 管制台外壳：顶部品牌条 + 导航 + 并发占用；无卡片、无阴影 */
export const OpsShell = ({ children }: { children: ReactNode }) => {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const quota = useQuotaStore();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col bg-rail">
      <header className="flex items-center gap-6 border-b px-5 py-2.5" style={{ borderColor: 'var(--color-wire)' }}>
        <div className="flex items-baseline gap-2">
          <span className="title-font text-lead text-ink">syncmesh</span>
          <span className="label-caps">合川零售 · 数据链路</span>
        </div>
        <nav className="flex items-center gap-4">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `text-dense ${isActive ? 'text-signal' : 'text-dim'} hover:text-ink`
              }
              style={({ isActive }) => ({ borderBottom: isActive ? '1px solid var(--color-signal)' : '1px solid transparent' })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-4 text-micro text-dim">
          <span className="num">
            并发 <span style={{ color: quota.active > 0 ? 'var(--color-signal)' : 'var(--color-dim)' }}>{quota.active}</span>/{quota.max}
            {quota.backingOff && <span style={{ color: 'var(--color-warn)' }}> · 退避中</span>}
          </span>
          <span className="num">{user?.display_name ?? ''}</span>
          <span className="border px-1.5 py-[1px]" style={{ borderColor: 'var(--color-wire)' }}>
            {user?.role ?? ''}
          </span>
          <button
            className="text-micro text-dim hover:text-danger"
            onClick={() => {
              logout();
              navigate('/login', { replace: true });
            }}
          >
            退出
          </button>
        </div>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
};
