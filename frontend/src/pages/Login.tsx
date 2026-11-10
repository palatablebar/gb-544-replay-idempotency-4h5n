import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { toHumanMessage } from '../utils/errorMessage';

const ACCOUNTS = [
  { role: 'owner', email: 'owner@hechuan.demo', note: '数据工程师 · 全部读写' },
  { role: 'operator', email: 'operator@hechuan.demo', note: '分析师 · 改映射 / 触发 / 重放' },
  { role: 'viewer', email: 'viewer@hechuan.demo', note: 'BI · 只读' },
];

export const LoginPage = () => {
  const login = useAuthStore((state) => state.login);
  const navigate = useNavigate();
  const [email, setEmail] = useState('owner@hechuan.demo');
  const [password, setPassword] = useState('Syncmesh@2026');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user = await login(email, password);
      navigate(user.role === 'viewer' ? '/targets' : '/sources', { replace: true });
    } catch (err) {
      setError(toHumanMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-stretch bg-rail">
      <div className="hidden flex-1 flex-col justify-between border-r px-10 py-8 md:flex" style={{ borderColor: 'var(--color-wire)' }}>
        <div>
          <div className="title-font text-[26px] text-ink">syncmesh</div>
          <div className="label-caps mt-1">异构数据源 · 增量同步 · 调度管制台</div>
          <p className="mt-8 max-w-[460px] text-dense leading-6 text-dim">
            把散落在 CSV 导出、JSONL 日志、外部 PostgreSQL 表和第三方 REST 接口里的同一份业务数据，
            按「源探测 → 字段映射 → 水位线增量 → 冲突策略落库 → 校验与拒绝行隔离」串成一条可保存、可重跑、可观测的管道。
          </p>
          <div className="mt-8 space-y-1.5 text-dense text-dim">
            <div>· 200 行门店 POS CSV / 2000 行会员中心快照 / 3 页电商 Mock REST</div>
            <div>· 冲突策略 skip / overwrite / reject 真实改变写入行为</div>
            <div>· 拒绝行带原始载荷进入 RejectedRecord，修完映射可原样重放</div>
          </div>
        </div>
        <div className="num text-micro text-dim">合川零售 · 120 家门店 · 数据平台组 6 人</div>
      </div>

      <div className="flex w-full max-w-[460px] flex-col justify-center px-10 py-10">
        <div className="label-caps mb-4">登录</div>
        <form onSubmit={submit} className="space-y-4">
          <label className="block">
            <span className="label-caps block pb-1">邮箱</span>
            <input
              type="email"
              className="w-full"
              value={email}
              autoComplete="username"
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="block">
            <span className="label-caps block pb-1">密码</span>
            <input
              type="password"
              className="w-full"
              value={password}
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error && (
            <div className="text-dense" style={{ color: 'var(--color-danger)' }}>
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full border py-2 text-dense font-semibold"
            style={{ borderColor: 'var(--color-signal)', color: 'var(--color-signal)' }}
          >
            {submitting ? '登录中…' : '进入管制台'}
          </button>
        </form>

        <div className="mt-8 border-t pt-4" style={{ borderColor: 'var(--color-wire)' }}>
          <div className="label-caps mb-2">演示账号（密码 Syncmesh@2026）</div>
          {ACCOUNTS.map((account) => (
            <button
              key={account.email}
              type="button"
              className="mb-1 flex w-full items-baseline justify-between gap-3 text-left"
              onClick={() => {
                setEmail(account.email);
                setPassword('Syncmesh@2026');
              }}
            >
              <span className="num text-dense text-ink">{account.email}</span>
              <span className="text-micro text-dim">{account.note}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
