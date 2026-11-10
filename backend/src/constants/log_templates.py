"""日志模板集中定义（≥22 条），utils/logger.py 只做序列化，worker 复用同一份模板。

新增一个阶段必须同时改：本文件、constants/enums.py 的 Stage、前端阶段步进文案。
"""
from __future__ import annotations

LOG_TEMPLATES: dict[str, str] = {
    # 数据源
    "SOURCE_REGISTERED": "source registered id={source_id} name={name} type={source_type}",
    "SOURCE_UPDATED": "source updated id={source_id} fields={fields}",
    "SOURCE_DELETED": "source deleted id={source_id} name={name}",
    "SOURCE_PROBE_START": "source probe start id={source_id} type={source_type}",
    "SOURCE_PROBE_OK": "source probe ok id={source_id} fields={fields} elapsed_ms={elapsed_ms}",
    "SOURCE_PROBE_FAIL": "source probe fail id={source_id} code={code} detail={detail}",
    "SOURCE_SAMPLE_SERVED": "source sample served id={source_id} rows={rows}",
    # 管道
    "PIPELINE_CREATED": "pipeline created id={pipeline_id} name={name} target={target_schema}.{target_table}",
    "PIPELINE_VALIDATED": "pipeline validated id={pipeline_id} mappings={mappings}",
    "PIPELINE_ENABLED": "pipeline enabled id={pipeline_id} cron={cron}",
    "PIPELINE_PAUSED": "pipeline paused id={pipeline_id}",
    "PIPELINE_DELETED": "pipeline deleted id={pipeline_id}",
    "PIPELINE_DUPLICATED": "pipeline duplicated from={source_id} to={pipeline_id}",
    "MAPPING_SAVED": "mapping saved pipeline={pipeline_id} rows={rows}",
    # 运行
    "RUN_ENQUEUED": "run enqueued run={run_id} pipeline={pipeline_id} trigger={trigger_type}",
    "RUN_LOCK_CONFLICT": "run lock conflict pipeline={pipeline_id} locked_until={locked_until}",
    "RUN_QUOTA_REJECTED": "run quota rejected user={user_id} active={active} max={max}",
    "RUN_STARTED": "run started run={run_id} pipeline={pipeline_id}",
    "RUN_STAGE_CHANGED": "run stage run={run_id} stage={stage}",
    "EXTRACT_START": "extract start run={run_id} source={source_type} watermark_from={watermark_from}",
    "EXTRACT_DONE": "extract done run={run_id} rows_read={rows_read} filtered_by_watermark={filtered}",
    "TRANSFORM_BATCH": "transform batch run={run_id} batch={batch_index} rows={rows} rejected={rejected}",
    "CONFLICT_HIT": "conflict hit run={run_id} strategy={strategy} keys={keys}",
    "LOAD_BATCH": "load batch run={run_id} batch={batch_index} written={written} skipped={skipped}",
    "VERIFY_OK": "verify ok run={run_id} expected={expected} actual={actual}",
    "VERIFY_REJECTED": "verify rejected run={run_id} rejected={rejected} codes={codes}",
    "RUN_SUCCEEDED": "run succeeded run={run_id} read={rows_read} written={rows_written} rejected={rows_rejected} watermark={watermark}",
    "RUN_PARTIAL": "run partial run={run_id} read={rows_read} written={rows_written} rejected={rows_rejected} watermark={watermark}",
    "RUN_FAILED": "run failed run={run_id} code={code} error={error}",
    "RUN_CANCELED": "run canceled run={run_id}",
    "RUN_RETRY_SCHEDULED": "run retry scheduled run={run_id} retry={retry_count} delay={delay}",
    "REPLAY_START": "replay start run={run_id} records={records} actor={actor_kind}:{actor_id}",
    "REPLAY_DONE": "replay done run={run_id} replayed={replayed} written={written} still_rejected={still_rejected}",
    # 调度 / 其它
    "SCHEDULE_SCAN": "schedule scan due={due} checked={checked}",
    "SCHEDULE_ENQUEUED": "schedule enqueued pipeline={pipeline_id} cron={cron}",
    "CLEANUP_STAGING": "cleanup staging run={run_id} dropped={dropped}",
    "AUDIT_WRITE_FAIL": "audit write failed action={action} error={error}",
    "API_KEY_ISSUED": "api key issued id={key_id} prefix={prefix} scopes={scopes}",
    "API_KEY_REVOKED": "api key revoked id={key_id}",
    "APP_STARTUP": "app startup env={env} seed_demo={seed_demo}",
    # seed
    "SEED_CREATED": "SEED_CREATED entity={entity} key={key}",
    "SEED_SKIPPED": "SEED_SKIPPED entity={entity} key={key}",
}
