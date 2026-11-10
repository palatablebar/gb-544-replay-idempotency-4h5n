export const ErrorCodeHint: Record<string, string> = {
  AUTH_REQUIRED: '请先登录',
  AUTH_INVALID: '登录状态无效，请重新登录',
  TOKEN_EXPIRED: '登录已过期，请重新登录',
  FORBIDDEN: '当前角色无权执行该操作',
  SOURCE_UNREACHABLE: '数据源不可达，检查路径/连接后重试探测',
  SOURCE_IN_USE: '数据源被管道引用，先改绑或删除管道',
  PIPELINE_INVALID_MAPPING: '映射校验失败：检查必填与目标列',
  PIPELINE_LOCKED: '这条管道正在跑，去看当前运行',
  WATERMARK_MISSING: '增量模式必须指定水位线列',
  TARGET_TABLE_MISSING: '目标表或目标列不存在',
  CONFLICT_KEY_ABSENT: '请配置冲突键',
  RUN_QUOTA_EXCEEDED: '并发运行数已达上限',
  RATE_LIMITED: '请求过于频繁，正在退避',
  API_KEY_INVALID: 'API Key 无效或已吊销',
  REPLAY_PAYLOAD_STALE: '原始载荷已过期，无法重放',
  REPLAY_EMPTY: '没有可重放的记录',
};

export const errorCodeHint = (code: string): string => ErrorCodeHint[code] ?? '操作失败，请查看 trace_id 定位日志';
