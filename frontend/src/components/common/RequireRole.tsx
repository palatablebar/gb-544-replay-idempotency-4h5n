import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import type { Role } from '../../types/models';
import { useAuthStore } from '../../stores/authStore';
import { tokenStore } from '../../api/client';

interface Props {
  roles: Role[];
  children: ReactNode;
  fallbackPath?: string;
  message?: string;
}

/**
 * 角色白名单。两个关键点：
 * 1. 已经登录但 user 尚未加载完成时不要直接踢到 /login（直链刷新场景），先显示加载态；
 * 2. 角色不匹配时挡回可访问页面并给出可读提示，而不是白屏。
 */
export const RequireRole = ({ roles, children, fallbackPath = '/targets', message }: Props) => {
  const user = useAuthStore((state) => state.user);
  const hasToken = Boolean(tokenStore.get());

  if (!hasToken) return <Navigate to="/login" replace />;

  if (!user) {
    return <div className="px-6 py-8 text-dense text-dim">加载会话…</div>;
  }

  if (!roles.includes(user.role)) {
    return (
      <div className="px-6 py-10">
        <div className="label-caps mb-2">权限不足</div>
        <p className="text-dense text-dim">
          {message ?? `当前角色（${user.role}）不能访问该页面。`}
        </p>
        <p className="mt-2 text-dense text-dim">正在跳转到 {fallbackPath}，可继续查看目标表与运行记录。</p>
        <Navigate to={fallbackPath} replace />
      </div>
    );
  }

  return <>{children}</>;
};
