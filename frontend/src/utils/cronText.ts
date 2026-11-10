const COMMON: Record<string, string> = {
  '0 2 * * *': '每天 02:00',
  '0 * * * *': '每小时整点',
  '*/15 * * * *': '每 15 分钟',
  '0 0 * * *': '每天 00:00',
};

export const cronText = (expression: string | null | undefined): string => {
  if (!expression) return '未设置';
  if (COMMON[expression]) return COMMON[expression];
  const parts = expression.trim().split(/\s+/);
  if (parts.length !== 5) return expression;
  const [minute, hour, day, month, weekday] = parts;
  if (minute === '*' && hour === '*') return '每分钟';
  if (hour === '*' && /^\d+$/.test(minute)) return `每小时第 ${minute} 分`;
  if (/^\d+$/.test(minute) && /^\d+$/.test(hour) && day === '*' && month === '*' && weekday === '*') {
    return `每天 ${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
  }
  return `cron ${expression}`;
};
