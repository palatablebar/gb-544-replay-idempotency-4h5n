# syncmesh · 异构数据源增量同步平台

同一份业务数据散落在 CSV 导出、JSONL 日志、外部 PostgreSQL 表和第三方 REST 接口里，syncmesh 把它们串成一条可保存、可重跑、可观测的同步管道：**源探测 → 字段映射与转换 → 按水位线增量拉取 → 按冲突策略落库 → 校验与失败行隔离 → 拒绝行重放**。

模拟客户：**合川零售**（区域连锁零售商，120 家门店，数据平台组 6 人 = 2 数据工程师 + 2 分析师 + 2 BI）。

## 1. 主要功能

- **四类数据源**：CSV 文件、JSONL 日志、PostgreSQL 表（同实例不同 schema）、内置 Mock REST（`/api/mock/rest/shop_orders`，分页 + 限流 + 偶发 5xx）。
- **探测**：CSV 探出分隔符/编码/字段清单；PG 表探出列与行数；Mock REST 返回第 1 页样本并提示「共 N 页」；结果写入 `DataSource.status` 与 `last_probed_at`。
- **映射与七种转换**：`trim` / `upper` / `lower` / `date_format` / `number_cast` / `concat` / `default`，每条映射可选必填、默认值、排序。
- **全量 / 增量**：增量按管道自己的 `watermark_column` 真实比较并推进水位线，重跑一次即「本批无新数据」。
- **三种冲突策略**：`skip`（ON CONFLICT DO NOTHING）/ `overwrite`（DO UPDATE）/ `reject`（预查已存在键 + 批次内重复键，拒绝而不覆盖）。
- **部分成功语义**：有拒绝行时 `status=partial`，`error_message` 为空但 `rows_rejected > 0`。
- **拒绝行与重放**：被拒行带原始载荷与原因码进入 `RejectedRecord`，修完映射后可单条/批量重放，写成功即从拒绝列表消失。
- **重放幂等与断点续跑**：重放按 `meta.replay_batches` 批次化——`batch_key`（run + 拒绝行集合的 sha256，唯一约束）保证同一批重复投递只生效一次；worker 执行前原子认领（`claim_token` 栅栏），broker 重投/并发点击都不会重复写；每条记录提交一次游标与心跳，进程中断后由 beat 扫描器（30s）重新入队、从断点续跑；`rows_written` 用 SQL 原子自增、`rows_rejected` 每个 checkpoint 按 `rejected_records` 真实行数重算，页面计数始终与库一致。
- **cron 调度**：worker 内同时跑 beat，每 `SCHEDULER_POLL_SECONDS` 扫描到期管道。
- **并发配额与管道锁**：`users.max_concurrent_runs`（默认 2）+ `meta.pipeline_locks` 唯一键锁；配额满返回 429、锁冲突返回 409。
- **审计日志**：源变更 / 管道启停 / 手动触发 / 重放 / Key 签发 全部落 `meta.audit_logs`。
- **API Key 触发**：`X-API-Key` 走 `/api/runs/trigger/api-key`、`/api/runs/{id}/replay/api-key`，库里只存 hash + 前缀。

## 2. 典型使用场景（一个真实工作日）

| 角色 | 账号 | 主要路由 | 权限边界 | 典型动作 |
|---|---|---|---|---|
| `owner`（数据工程师） | `owner@hechuan.demo` | `/sources`、`/pipelines`、`/pipelines/:id/mapping`、`/runs`、`/runs/:id`、`/targets` | 全部读写；可改源配置、删管道、签 API Key、改并发上限 | 登记 POS CSV 与会员库、配水位线与冲突策略、调映射、批量重放 |
| `operator`（分析师） | `operator@hechuan.demo` | `/pipelines`、`/pipelines/:id/mapping`、`/runs`、`/runs/:id`、`/targets`（`/sources` 只读） | 可改映射、可触发运行、可重放；不能改源连接、不能删管道、不能发 Key | 跑批后核对行数、按口径调转换、重放被拒门店行、盯 `partial` |
| `viewer`（BI） | `viewer@hechuan.demo` | `/targets`、`/runs`、`/runs/:id` | 只读；不能触发、不能重放、不能改映射（访问映射页被挡回 `/targets` 并给出提示） | 按订单号查落库结果、用 `_sync_run_id` 追到具体运行 |

**工作日剧本**（seed 后的干净状态即可复现）：

1. 周一 09:00 `owner` 登录，`/sources` 里已有 3 个源：`store_sales_20261109.csv`（csv）、`members`（postgres_table，指向 `target.members_source`）、`mock_shop_orders`（mock_rest）。
2. 09:20 逐个「探测」：CSV 探出 `store_no/sale_date/sku/qty/amount/updated_at`；`members` 探出 `member_id/mobile/tier/updated_at`；`mock_shop_orders` 回第 1 页并提示「共 3 页」。
3. 09:40 `/pipelines` 3 条管道：`target.store_sales` / `target.members` / `target.channel_orders`，`sync_mode` 全为 `incremental`；水位线分别是 `updated_at` / `updated_at` / `order_id`。
4. 10:10 `/pipelines/:id/mapping`：`sale_date` 走 `date_format`、`amount` 走 `number_cast`、`store_no` 走 `trim`；`channel_orders` 的 `member_id` 勾 `is_required`，冲突键 `order_id`、策略 `reject`。
5. 11:00 手动触发全量：`target.store_sales` 从 50 行涨到 250 行（CSV 200 行全部落库），`_sync_run_id` 指向这次运行。
6. 11:30 三条管道 cron `0 2 * * *`，此后每天 02:00 自动增量。
7. 周二 02:00 电商侧补推一批含重复 `order_id` 且部分 `member_id` 为空的订单（`POST /api/mock/rest/shop_orders/push` 开启补推批次）；再跑一次 `channel_orders`：**12 行命中冲突被 reject、3 行缺主键**（`required_missing`），`error_message` 为空但 `rows_rejected=15` → `partial`。
8. 周二 09:20 `operator` 打开 `/runs/:id`，`<DiffPanel>` 逐列看差异；拒绝记录按原因码分成 `conflict_rejected` 12 条 + `required_missing` 3 条。
9. 09:40 在映射页给 `member_id` 补 `default` 转换后保存，回 `/runs/:id` 批量重放那 3 行 → 3 行写成功、`rows_rejected` 降到 12。
10. 10:00 `viewer` 登录 `/targets`，按 `order_id` 搜订单，核对 `_synced_at` 与 `_sync_run_id`。

## 3. 快速启动

```bash
cp .env.example .env
docker compose up -d --build
```

- 后端首次启动会执行 `alembic upgrade head`（建 `meta` / `staging` / `target` 三个 schema 与三张目标表），
  随后在 `SEED_DEMO=true` 时自动执行一次幂等 seed，失败只记 WARNING、不影响 healthcheck。
- 前端 <http://localhost:18113>，API 文档 <http://localhost:19113/docs>，数据库映射 `localhost:17613`。

**数据库镜像说明**：题目要求 PostgreSQL 15，本实现使用本机已拉取的 `postgres:16-alpine`（16 对 15 完全兼容，
schema/ON CONFLICT/JSONB 语法一致），`TESTING.md` 中已注明。

## 4. 演示数据初始化

```bash
docker compose exec backend python -m scripts.seed_demo
```

或依赖 `.env` 里的 `SEED_DEMO=true` 由 backend 启动时自动执行一次。

**seed 是幂等的**：自然键为文件 checksum / `DataSource.name` / `SyncPipeline.name + target_table` / 目标表主键。
重复执行不重复插入、不重复上传、不覆盖用户改过的映射；第二次执行的输出全是 `SEED_SKIPPED`（这是幂等的肉眼证据）。

seed 生成：

- `store_sales_20261109.csv`：200 行门店销售（2 行金额带千分位/货币符号、1 行非 ISO 日期，用于演示 `number_cast` / `date_format`）。
- `member_profile_20261109.jsonl`：100 行会员画像（备用练习源）。
- `target.members_source`：2000 行会员中心快照（`dsn_alias=default` 指向同一实例）。
- Mock REST：3 页 × 50 行 = 150 行（`page=1..3`）。
- 三张目标表各 50 行初始数据（`target.store_sales` / `target.members` / `target.channel_orders`）。
- 3 条管道 + 各自 `FieldMapping`（水位线、冲突键、cron `0 2 * * *` 与剧本一致）。
- 3 个账号（见上表），密码 **`Syncmesh@2026`**，`max_concurrent_runs` 默认 2。

## 5. 演示账号

| 角色 | 邮箱 | 密码 |
|---|---|---|
| owner | `owner@hechuan.demo` | `Syncmesh@2026` |
| operator | `operator@hechuan.demo` | `Syncmesh@2026` |
| viewer | `viewer@hechuan.demo` | `Syncmesh@2026` |

## 6. 本地开发

```bash
# 前端
cd frontend && npm install --registry=https://registry.npmjs.org && npm run dev

# 后端
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8000

# worker（本地用 -B 同时跑 beat；容器里由同一条 CMD 带 -B 启动）
cd worker && celery -A worker_src.config.celery_app worker -B -l info
```

> 容器内 `worker/src` 被复制为 `worker_src` 包（见 `worker/Dockerfile`），避免与 backend 的顶层包 `src` 同名冲突；
> worker 通过 `PYTHONPATH=/app/backend` 复用 backend 的模型、服务与日志模板，不重复实现业务逻辑。

## 7. 访问地址

- 前端：<http://localhost:18113>
- API 文档：<http://localhost:19113/docs>、健康检查 <http://localhost:19113/api/health>
- 内置 Mock REST：`http://localhost:19113/api/mock/rest/shop_orders?page=1&page_size=50`
  - 分页：`page` / `page_size` / `total_pages`
  - 限流：每分钟 120 次，超出返回 429 与 `retry_after`
  - 偶发 5xx：每 9 次请求注入一次 500，用于验证 worker 的退避重试
  - 补推批次开关：`POST /api/mock/rest/shop_orders/push` 开启、`DELETE` 重置

## 8. 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Tailwind 3（自定义 oklch token）+ Zustand + TanStack Query + TanStack Table + React Router 6 |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0（typed declarative）+ Pydantic v2 + passlib[bcrypt] + pyjwt + croniter + pandas |
| Worker | Celery 5（worker + beat 同容器）+ Redis 7 broker/backend，四类连接器与同步编排全在 worker 进程内 |
| 数据库 | PostgreSQL 16（单实例三 schema：`meta` 平台表 / `staging` 运行中间表 / `target` 业务目标表） |
| 缓存 / 队列 | Redis 7（Celery、限流滑动窗口、Mock REST 状态开关） |
| 部署 | Docker Compose（5 服务：frontend / backend / worker / db / redis），Nginx 托管前端并反代 `/api/` |

## 9. 目录结构

```
gb-544/
├── docker-compose.yml           # 5 服务、命名卷、healthcheck、depends_on 健康条件
├── .env / .env.example / .gitignore / .dockerignore
├── frontend/
│   ├── Dockerfile / nginx.conf  # 构建后由 nginx 托管，/api/ 反代 backend
│   └── src/
│       ├── api/                 # client + auth/source/pipeline/mapping/run/rejected/target/apiKey
│       ├── stores/              # auth/source/pipeline/mapping/run/quota
│       ├── types/               # models/api/table
│       ├── components/common/   # SampleDataGrid/RunStatusPill/SourceBadge/MappingRowEditor/DiffPanel/EmptyState/RequireRole/CronField
│       ├── components/layout/   # OpsShell/PipelineTree/RunTimeline/InspectorPanel
│       ├── hooks/               # useRunPolling/useMappingDraft/useSourceProbe/useAuthGuard
│       ├── pages/               # Sources/Pipelines/MappingEditor/Runs/RunDetail/Targets/Login
│       ├── router/              # index + guards
│       ├── utils/               # watermark/rowDiff/errorMessage/cronText/formatCount
│       ├── constants/           # sources/sync/transforms/auditActions/errorCodes
│       └── styles/              # tokens.css（oklch token）+ global.css
├── backend/
│   ├── Dockerfile / entrypoint.sh / requirements.txt / alembic.ini
│   ├── scripts/seed_demo.py     # 幂等 seed
│   └── src/
│       ├── routes/              # auth/source/pipeline/run/rejected/target/api_key/audit/health/meta/mock
│       ├── controllers/         # 每个路由一个 controller
│       ├── services/            # auth/source/pipeline/mapping/run/replay/extract/transform/load/verify/quota/scheduler/api_key/audit
│       ├── models/              # user/data_source/sync_pipeline/field_mapping/sync_run/rejected_record/replay_batch/api_key/audit_log/pipeline_lock
│       ├── schemas/             # auth/source/pipeline/mapping/run/rejected/replay/target/common
│       ├── middlewares/         # auth/rbac/api_key/audit_logger/rate_limit/error_handler
│       ├── utils/               # jwt/password/logger/formatters/watermark/backoff/checksum/csv_reader/jsonl_reader/mock_rest/errors/redis_client
│       ├── constants/           # enums/transforms/error_codes/log_templates/messages/limits/roles
│       ├── config/              # settings/database/celery_app/app
│       └── migrations/          # alembic env + versions/0001_initial（三个 schema 与目标表）+ 0002_replay_batches（重放批次表）
└── worker/
    ├── Dockerfile / healthcheck.sh
    └── src/
        ├── tasks/               # sync_task/schedule_task/replay_task/replay_resume_task/cleanup_task/heartbeat_task
        ├── pipelines/           # extract/incremental/transform/load/verify
        ├── connectors/          # csv/jsonl/postgres/rest
        ├── core/                # progress/lock/retry/storage
        ├── constants/           # stages/reason_codes/tuning
        └── config/              # settings/celery_app
```

三个 schema 的职责：`meta` 放平台自身表（用户/源/管道/映射/运行/拒绝/Key/审计/锁）；
`staging` 每次运行先落地 `staging.sync_<pipeline>` 再校验写入；`target` 放业务目标表（含 `_sync_run_id`、`_synced_at`）。

**严禁合并职责到单一文件。** 即使是简单功能，也按上述分层拆分，确保每一个小改动都至少触达 3-5 个文件。

## 10. 环境变量

| 键 | 默认值 | 必填 | 作用 |
|---|---|---|---|
| `COMPOSE_PROJECT_NAME` | `syncmesh` | 否 | 容器名前缀 `${COMPOSE_PROJECT_NAME:-syncmesh}-<role>` |
| `FRONTEND_PORT` | `18113` | 否 | 前端宿主机端口 |
| `BACKEND_PORT` | `19113` | 否 | 后端宿主机端口 |
| `DB_PORT` | `17613` | 否 | PostgreSQL 映射端口 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `syncmesh` / `syncmesh` / `syncmesh_pw_2026` | 是 | 业务库连接 |
| `DB_ADMIN_PASSWORD` | `postgres_admin_2026` | 否 | 预留管理员口令 |
| `JWT_SECRET` | 示例值 | 是 | JWT 签名（生产必须替换） |
| `API_KEY_PEPPER` | 示例值 | 是 | API Key hash 加盐 |
| `REDIS_URL` | `redis://redis:6379/0` | 是 | Celery broker/backend、限流 |
| `SOURCE_DIR` | `/data/sources` | 是 | 上传的 CSV/JSONL（`source_data` 卷） |
| `ARTIFACT_DIR` | `/data/artifacts` | 是 | 运行报告/拒绝导出（`artifact_data` 卷） |
| `MAX_UPLOAD_MB` | `200` | 否 | 上传大小上限（与 `client_max_body_size` 对齐） |
| `DEFAULT_MAX_CONCURRENT_RUNS` | `2` | 否 | 用户默认并发上限 |
| `MOCK_REST_BASE_URL` | `http://backend:8000` | 是 | worker 拉 Mock REST 的基地址 |
| `SCHEDULER_POLL_SECONDS` | `30` | 否 | beat 扫描 cron 到期的间隔 |
| `SEED_DEMO` | `true` | 否 | backend 启动是否自动执行一次 seed |

## 11. Docker 部署说明

- 端口映射：`frontend ${FRONTEND_PORT:-18113}:80`、`backend ${BACKEND_PORT:-19113}:8000`、`db ${DB_PORT:-17613}:5432`；`worker` 与 `redis` 不暴露端口。
- 四个命名卷：`db_data`（PG 数据）、`redis_data`（AOF）、`source_data`（backend 写 / worker 读的源文件）、`artifact_data`（运行报告与拒绝行导出）。
- Nginx：`location /api/ { proxy_pass http://backend:8000/; }` 反代后端根路由；`client_max_body_size 200m`；`proxy_read_timeout 600s`；`/api/runs/` 与 `/api/targets/` 关闭 `proxy_buffering` 便于长轮询。
- 常见问题：
  - `db` 初始化失败（旧卷 schema 冲突）→ `docker compose down -v` 后重来。
  - 上传 413 → 同时调大 `MAX_UPLOAD_MB` 与 `nginx.conf` 的 `client_max_body_size`。
  - 管道一直卡住 → `docker compose logs -f worker` 看是否卡在管道锁；`meta.pipeline_locks.locked_until` 过期后由 `cleanup_task` 清理。
  - `partial` 与 `failed` 的区别：`partial` 是主流程跑完但有拒绝行（去 `/runs/:id` 重放）；`failed` 是阶段异常（看 `error_message` 与 `retry_count`）。
  - 手工触发一次运行：`curl -X POST http://localhost:19113/api/pipelines/<id>/trigger -H "Authorization: Bearer <token>"`。

## 12. 枚举出现位置清单

> 五组枚举在前后端**各自定义一份**（`backend/src/constants/enums.py` 与 `frontend/src/constants/*.ts`），不做代码生成，
> 靠本表保持一致。新增值时：后端加枚举 + `ENUM_LABELS`、前端加常量 + 展示名、README 本表补一行。

### SourceType（数据源类型）

| 文件 | 用途 |
|---|---|
| `backend/src/constants/enums.py` | `class SourceType(str, Enum)` |
| `backend/src/schemas/source.py` | `SOURCE_TYPES` 校验白名单 |
| `backend/src/services/source_service.py` | `SOURCE_TYPE_CONFIG_KEYS`、探测分发 |
| `backend/src/services/extract_service.py` | 抽取器选择（csv/jsonl/pg/rest） |
| `backend/src/controllers/meta_controller.py` | `/meta/enums` 暴露中文名 |
| `backend/src/constants/log_templates.py` | `SOURCE_PROBE_*` 模板带 `source_type` |
| `worker/src/pipelines/extract.py` | `CONNECTORS` 连接器映射 |
| `frontend/src/constants/sources.ts` | `SourceType` + `SourceTypeMeta`（图标语义/配置字段） |
| `frontend/src/components/common/SourceBadge.tsx` | 徽标颜色与文案 |
| `frontend/src/pages/Sources.tsx` | 配置表单分支（meta.configFields） |
| `frontend/src/pages/MappingEditor.tsx` | 样本列宽策略取源类型 |
| `README.md` | 本表 |

### SyncMode（同步模式）

| 文件 | 用途 |
|---|---|
| `backend/src/constants/enums.py` | `class SyncMode(str, Enum)` |
| `backend/src/schemas/pipeline.py` | 请求体默认值 |
| `backend/src/services/verify_service.py` | `incremental` 必须有 `watermark_column` |
| `backend/src/services/pipeline_service.py` | 创建/更新落库 |
| `backend/src/constants/log_templates.py` | `EXTRACT_START` 带水位线 |
| `worker/src/pipelines/incremental.py` | 增量过滤分支 |
| `worker/src/tasks/sync_task.py` | 选择过滤与水位线推进 |
| `frontend/src/constants/sync.ts` | `SyncMode` + `SyncModeLabel` |
| `frontend/src/pages/Pipelines.tsx` | 行内「增量/全量」标记 |
| `frontend/src/pages/MappingEditor.tsx` | 水位线提示条 |
| `README.md` | 本表 |

### RunStatus（运行状态）

| 文件 | 用途 |
|---|---|
| `backend/src/constants/enums.py` | `class RunStatus` + `terminal()` |
| `backend/src/schemas/run.py` | `serialize_run` 行数三元组与水位线文案 |
| `backend/src/services/run_service.py` | 状态机、取消、入队 |
| `backend/src/services/quota_service.py` | `ACTIVE_STATUSES = queued/running` |
| `backend/src/controllers/run_controller.py` | 列表/详情/触发/重放 |
| `backend/src/utils/formatters.py` | 中文名 `ENUM_LABELS` |
| `worker/src/core/progress.py` | `mark_running` / `finish` 回写 |
| `worker/src/pipelines/verify.py` | `final_status`（succeeded/partial/failed） |
| `frontend/src/constants/sync.ts` | `RunStatus` + `RunStatusLabel` + `RunStatusToken` + 终态集合 |
| `frontend/src/components/common/RunStatusPill.tsx` | 六态胶囊 + 三元组 |
| `frontend/src/hooks/useRunPolling.ts` | 终态即停轮询 |
| `frontend/src/pages/Runs.tsx` / `RunDetail.tsx` | 过滤与阶段步进 |
| `README.md` | 本表 |

### ReplayBatchStatus（重放批次状态）

| 文件 | 用途 |
|---|---|
| `backend/src/constants/enums.py` | `class ReplayBatchStatus` + `active()` / `terminal()` |
| `backend/src/models/replay_batch.py` | 批次表：幂等键 / 游标 / 认领令牌 / 心跳 |
| `backend/src/services/replay_service.py` | 幂等 get-or-create、原子认领、checkpoint、中断扫描 |
| `backend/src/services/run_service.py` | 重放入队（幂等去重 / 终态重新激活）、详情带批次进度 |
| `worker/src/tasks/replay_task.py` | 认领执行、游标断点续跑、原子计数 |
| `worker/src/tasks/replay_resume_task.py` | beat 每 30s 扫描心跳过期批次重新入队 |
| `frontend/src/constants/sync.ts` | `ReplayBatchStatusLabel` + `ACTIVE_REPLAY_STATUSES` |
| `frontend/src/pages/RunDetail.tsx` | 批次进度展示与幂等提示 |
| `README.md` | 本表 |

### ConflictStrategy（冲突策略）
| 文件 | 用途 |
|---|---|
| `backend/src/constants/enums.py` | `class ConflictStrategy` |
| `backend/src/schemas/pipeline.py` | 请求字段 |
| `backend/src/services/load_service.py` | `INSERT ... ON CONFLICT` 三个分支 + 批次内重复键 |
| `backend/src/services/verify_service.py` | 必须有 `conflict_key`（否则 `CONFLICT_KEY_ABSENT`） |
| `backend/src/constants/messages.py` | 三种策略的说明文案 `CONFLICT_STRATEGY_HELP` |
| `backend/src/constants/log_templates.py` | `CONFLICT_HIT` 带策略 |
| `worker/src/tasks/sync_task.py` | 传入策略给写入 |
| `frontend/src/constants/sync.ts` | `ConflictStrategy` + `ConflictStrategyLabel` |
| `frontend/src/pages/Pipelines.tsx` | 策略徽标 |
| `frontend/src/pages/RunDetail.tsx` | `conflict_rejected` 原因展示 |
| `README.md` | 本表 |

### TransformType（字段转换类型）

| 文件 | 用途 |
|---|---|
| `backend/src/constants/enums.py` | `class TransformType` |
| `backend/src/constants/transforms.py` | `TRANSFORM_PARAM_SPECS` 参数校验规则 |
| `backend/src/services/transform_service.py` | 转换器注册表 `TRANSFORM_REGISTRY` + `transform_row` |
| `backend/src/services/mapping_service.py` | 保存前参数校验、试运行 |
| `backend/src/utils/formatters.py` | 中文名 |
| `backend/src/constants/log_templates.py` | `TRANSFORM_BATCH` 拒绝计数 |
| `backend/src/constants/error_codes.py` | 转换失败统一 `transform_failed` |
| `worker/src/pipelines/transform.py` | 批次转换编排 |
| `frontend/src/constants/transforms.ts` | `TransformType` + `TransformLabel` + `TransformParamSpecs` |
| `frontend/src/components/common/MappingRowEditor.tsx` | 参数表单分支 |
| `frontend/src/pages/MappingEditor.tsx` | before/after 样本列 |
| `README.md` | 本表 |

**新增 `TransformType = "regex_replace"` 需要触达的 9+ 个文件**：`enums.py` → `transforms.py`（`pattern`/`replacement`）
→ `transform_service.py`（注册转换器）→ `formatters.py`（中文名）→ `log_templates.py`（失败日志带 pattern）
→ `error_codes.py`（非法正则）→ `frontend/constants/transforms.ts` → `MappingRowEditor.tsx`（参数分支）→ `README.md`。

## 13. License

MIT License · 2026 · 合川零售数据平台组（示例作者占位）
