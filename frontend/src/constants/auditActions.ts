export const AuditActionLabel: Record<string, string> = {
  'auth.login': '登录',
  'source.create': '登记数据源',
  'source.update': '更新数据源',
  'source.delete': '删除数据源',
  'source.probe': '探测数据源',
  'pipeline.create': '创建管道',
  'pipeline.update': '更新管道',
  'pipeline.activate': '启用管道',
  'pipeline.pause': '暂停管道',
  'pipeline.delete': '删除管道',
  'mapping.save': '保存映射',
  'run.trigger': '触发运行',
  'run.replay': '重放拒绝行',
  'run.cancel': '取消运行',
  'rejected.replay': '单条重放',
  'apikey.issue': '签发 API Key',
  'apikey.revoke': '吊销 API Key',
};

export const auditActionLabel = (action: string): string => AuditActionLabel[action] ?? action;
