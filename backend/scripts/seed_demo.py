"""幂等演示数据入口：`docker compose exec backend python -m scripts.seed_demo`。

自然键：文件 checksum / DataSource.name / SyncPipeline.name+target_table / 目标表主键。
重复执行只会输出 SEED_SKIPPED，不重复插入、不覆盖用户改过的映射。
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.database import engine, session_scope
from src.config.settings import settings
from src.constants.enums import (
    ConflictStrategy,
    PipelineStatus,
    SourceStatus,
    SourceType,
    SyncMode,
    TransformType,
)
from src.constants.log_templates import LOG_TEMPLATES  # noqa: F401
from src.constants.roles import ROLE_OPERATOR, ROLE_OWNER, ROLE_VIEWER
from src.models.data_source import DataSource
from src.models.field_mapping import FieldMapping
from src.models.sync_pipeline import SyncPipeline
from src.models.user import User
from src.utils.checksum import sha256_bytes
from src.utils.password import hash_password

DEMO_PASSWORD = "Syncmesh@2026"
DEMO_USERS = [
    ("owner@hechuan.demo", "合川零售 · 数据工程师", ROLE_OWNER),
    ("operator@hechuan.demo", "合川零售 · 分析师", ROLE_OPERATOR),
    ("viewer@hechuan.demo", "合川零售 · BI", ROLE_VIEWER),
]

CSV_FILENAME = "store_sales_20261109.csv"
JSONL_FILENAME = "member_profile_20261109.jsonl"
CRON_DAILY_2AM = "0 2 * * *"

CREATED = 0
SKIPPED = 0


def _log(kind: str, entity: str, key: str) -> None:
    global CREATED, SKIPPED
    if kind == "SEED_CREATED":
        CREATED += 1
    else:
        SKIPPED += 1
    print(f"{kind} entity={entity} key={key}", flush=True)


def _created(entity: str, key: str) -> None:
    _log("SEED_CREATED", entity, key)


def _skipped(entity: str, key: str) -> None:
    _log("SEED_SKIPPED", entity, key)


# ---------------------------------------------------------------- 文件数据 ----


def build_csv_text() -> str:
    """200 行门店销售；3 行为脏数据（2 行金额带千分位/货币符号，1 行非 ISO 日期）。

    用 csv.writer 生成，含逗号的金额（`1,280.00`）会被正确加引号，避免切列。
    """
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["store_no", "sale_date", "sku", "qty", "amount", "updated_at"])
    for index in range(200):
        store_no = f"S{(index % 12) + 1:03d}"
        sku = f"SKU{index:04d}"
        qty = (index % 7) + 1
        amount = f"{(index % 53) * 8.4 + 12.5:.2f}"
        sale_date = "2026-11-09"
        updated_at = f"2026-11-09 {9 + (index % 10):02d}:{(index * 3) % 60:02d}:00"
        if index == 17:
            amount = "1,280.00"  # 千分位 → 需要 number_cast 清理
        elif index == 88:
            amount = "¥980.50"  # 货币符号 → 需要 number_cast 清理
        elif index == 133:
            sale_date = "2026/11/09"  # 非 ISO → 需要 date_format
        writer.writerow([store_no, sale_date, sku, qty, amount, updated_at])
    return buffer.getvalue()


def build_jsonl_text() -> str:
    import json

    lines = []
    for index in range(100):
        payload = {
            "member_id": f"M{index + 1:04d}",
            "tier": ["金卡", "银卡", "普卡"][index % 3],
            "city": ["成都", "绵阳", "德阳", "宜宾"][index % 4],
            "updated_at": f"2026-11-09 {(index % 12) + 8:02d}:{index % 60:02d}:00",
        }
        lines.append(json.dumps(payload, ensure_ascii=False))
    return "\n".join(lines) + "\n"


def ensure_file(directory: Path, filename: str, content: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    checksum = sha256_bytes(content.encode("utf-8"))
    if path.exists() and sha256_bytes(path.read_bytes()) == checksum:
        _skipped("SourceFile", filename)
        return path
    if not path.exists():
        path.write_text(content, encoding="utf-8")
        _created("SourceFile", filename)
    else:
        path.write_text(content, encoding="utf-8")
        _created("SourceFile", f"{filename} (rewritten)")
    return path


# ---------------------------------------------------------------- 账号 ----


def seed_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for email, display_name, role in DEMO_USERS:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=display_name,
                role=role,
                is_active=True,
                max_concurrent_runs=2,
                created_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.flush()
            _created("User", email)
        else:
            _skipped("User", email)
        users[role] = user
    db.commit()
    return users


# ---------------------------------------------------------------- 目标表 ----


def seed_target_tables() -> None:
    members_source_rows = []
    for index in range(2000):
        member_id = f"M{index + 1:04d}"
        updated_at = datetime(2026, 11, 1, tzinfo=timezone.utc) + timedelta(minutes=index * 4)
        members_source_rows.append(
            {
                "member_id": member_id,
                "mobile": f"138{index:08d}"[:11],
                "tier": ["金卡", "银卡", "普卡"][index % 3],
                "updated_at": updated_at.replace(tzinfo=None),
            }
        )

    store_sales_rows = []
    for index in range(50):
        store_sales_rows.append(
            {
                "store_no": f"S9{(index % 5) + 1:02d}",
                "sale_date": datetime(2026, 11, 1).date(),
                "sku": f"SKUOLD{index:03d}",
                "qty": (index % 5) + 1,
                "amount": round(30.5 + index * 1.25, 2),
                "updated_at": datetime(2026, 11, 1, 8, index % 60),
            }
        )

    members_rows = []
    for index in range(50):
        members_rows.append(
            {
                "member_id": f"M{index + 1:04d}",
                "mobile": f"139{index:08d}"[:11],
                "tier": ["金卡", "银卡", "普卡"][index % 3],
                "updated_at": datetime(2026, 10, 1, 9, index % 60),
            }
        )

    channel_rows = []
    for index in range(50):
        channel_rows.append(
            {
                "order_id": 901 + index,
                "member_id": f"M{index + 1:04d}",
                "amount": round(56.8 + index * 2.1, 2),
                "channel": ["mall", "mini", "app"][index % 3],
                "order_status": "paid",
                "updated_at": datetime(2026, 10, 28, 12, index % 60),
            }
        )

    statements: list[tuple[str, str, list[dict[str, Any]], str]] = [
        (
            "members_source",
            f'INSERT INTO {settings.target_schema}.members_source '
            "(member_id, mobile, tier, updated_at) VALUES (:member_id, :mobile, :tier, :updated_at) "
            "ON CONFLICT (member_id) DO NOTHING",
            members_source_rows,
            "member_id",
        ),
        (
            "store_sales",
            f'INSERT INTO {settings.target_schema}.store_sales '
            "(store_no, sale_date, sku, qty, amount, updated_at) "
            "VALUES (:store_no, :sale_date, :sku, :qty, :amount, :updated_at) "
            "ON CONFLICT (store_no, sku) DO NOTHING",
            store_sales_rows,
            "store_no+sku",
        ),
        (
            "members",
            f'INSERT INTO {settings.target_schema}.members '
            "(member_id, mobile, tier, updated_at) VALUES (:member_id, :mobile, :tier, :updated_at) "
            "ON CONFLICT (member_id) DO NOTHING",
            members_rows,
            "member_id",
        ),
        (
            "channel_orders",
            f'INSERT INTO {settings.target_schema}.channel_orders '
            "(order_id, member_id, amount, channel, order_status, updated_at) "
            "VALUES (:order_id, :member_id, :amount, :channel, :order_status, :updated_at) "
            "ON CONFLICT (order_id) DO NOTHING",
            channel_rows,
            "order_id",
        ),
    ]

    with engine.begin() as conn:
        for table, sql, rows, key in statements:
            before = conn.execute(
                text(f"SELECT count(*) FROM {settings.target_schema}.{table}")
            ).scalar_one()
            conn.execute(text(sql), rows)
            after = conn.execute(
                text(f"SELECT count(*) FROM {settings.target_schema}.{table}")
            ).scalar_one()
            if after > before:
                _created("TargetRows", f"{table} (+{after - before})")
            else:
                _skipped("TargetRows", f"{table} ({after})")


# ---------------------------------------------------------------- 数据源 ----


def seed_sources(db, owner: User, csv_path: Path, jsonl_path: Path) -> dict[str, DataSource]:
    definitions = [
        {
            "name": CSV_FILENAME,
            "source_type": SourceType.CSV.value,
            "config": {
                "upload_path": str(csv_path),
                "delimiter": ",",
                "has_header": True,
                "encoding": "utf-8",
            },
            "probe": {
                "columns": ["store_no", "sale_date", "sku", "qty", "amount", "updated_at"],
                "row_count": 200,
            },
        },
        {
            "name": "members",
            "source_type": SourceType.POSTGRES_TABLE.value,
            "config": {
                "dsn_alias": "default",
                "schema": settings.target_schema,
                "table": "members_source",
            },
            "probe": {
                "columns": ["member_id", "mobile", "tier", "updated_at"],
                "row_count": 2000,
            },
        },
        {
            "name": "mock_shop_orders",
            "source_type": SourceType.MOCK_REST.value,
            "config": {
                "endpoint": "/api/mock/rest/shop_orders",
                "page_size": 50,
                "cursor_field": "order_id",
            },
            "probe": {
                "columns": [
                    "order_id",
                    "member_id",
                    "amount",
                    "channel",
                    "order_status",
                    "updated_at",
                ],
                "row_count": 150,
                "total_pages": 3,
            },
        },
    ]
    sources: dict[str, DataSource] = {}
    for definition in definitions:
        source = db.query(DataSource).filter(DataSource.name == definition["name"]).one_or_none()
        if source is None:
            source = DataSource(
                owner_id=owner.id,
                name=definition["name"],
                source_type=definition["source_type"],
                config_json=definition["config"],
                status=SourceStatus.OK.value,
                last_probed_at=datetime(2026, 11, 9, 9, 20, tzinfo=timezone.utc),
                probe_result_json={
                    **definition["probe"],
                    "delimiter": definition["config"].get("delimiter"),
                    "encoding": definition["config"].get("encoding", "utf-8"),
                    "has_header": True,
                    "sample": [],
                },
                created_at=datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc),
            )
            db.add(source)
            db.flush()
            _created("DataSource", definition["name"])
        else:
            _skipped("DataSource", definition["name"])
        sources[definition["name"]] = source
    db.commit()
    return sources


# ---------------------------------------------------------------- 管道 ----


PIPELINE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "门店销售日同步",
        "source_name": CSV_FILENAME,
        "target_table": "store_sales",
        "watermark_column": "updated_at",
        "conflict_strategy": ConflictStrategy.OVERWRITE.value,
        "conflict_key": "store_no,sku",
        "mappings": [
            ("store_no", "store_no", TransformType.TRIM.value, {}, False),
            ("sale_date", "sale_date", TransformType.DATE_FORMAT.value,
             {"from": "%Y/%m/%d", "to": "%Y-%m-%d"}, True),
            ("sku", "sku", TransformType.TRIM.value, {}, False),
            ("qty", "qty", TransformType.TRIM.value, {}, False),
            ("amount", "amount", TransformType.NUMBER_CAST.value,
             {"decimal_places": 2, "strip": "¥,元, "}, False),
            ("updated_at", "updated_at", TransformType.TRIM.value, {}, False),
        ],
    },
    {
        "name": "会员中心增量同步",
        "source_name": "members",
        "target_table": "members",
        "watermark_column": "updated_at",
        "conflict_strategy": ConflictStrategy.OVERWRITE.value,
        "conflict_key": "member_id",
        "mappings": [
            ("member_id", "member_id", TransformType.TRIM.value, {}, True),
            ("mobile", "mobile", TransformType.TRIM.value, {}, False),
            ("tier", "tier", TransformType.TRIM.value, {}, False),
            ("updated_at", "updated_at", TransformType.TRIM.value, {}, False),
        ],
    },
    {
        "name": "电商订单增量同步",
        "source_name": "mock_shop_orders",
        "target_table": "channel_orders",
        "watermark_column": "order_id",
        "conflict_strategy": ConflictStrategy.REJECT.value,
        "conflict_key": "order_id",
        "mappings": [
            ("order_id", "order_id", TransformType.TRIM.value, {}, True),
            ("member_id", "member_id", TransformType.TRIM.value, {}, True),
            ("amount", "amount", TransformType.NUMBER_CAST.value,
             {"decimal_places": 2, "strip": "¥,元, "}, False),
            ("channel", "channel", TransformType.TRIM.value, {}, False),
            ("order_status", "order_status", TransformType.TRIM.value, {}, False),
            ("updated_at", "updated_at", TransformType.TRIM.value, {}, False),
        ],
    },
]


def seed_pipelines(db, owner: User, sources: dict[str, DataSource]) -> None:
    for definition in PIPELINE_DEFINITIONS:
        source = sources[definition["source_name"]]
        pipeline = (
            db.query(SyncPipeline)
            .filter(
                SyncPipeline.name == definition["name"],
                SyncPipeline.target_table == definition["target_table"],
            )
            .one_or_none()
        )
        if pipeline is None:
            pipeline = SyncPipeline(
                owner_id=owner.id,
                source_id=source.id,
                name=definition["name"],
                target_schema=settings.target_schema,
                target_table=definition["target_table"],
                sync_mode=SyncMode.INCREMENTAL.value,
                watermark_column=definition["watermark_column"],
                conflict_strategy=definition["conflict_strategy"],
                conflict_key=definition["conflict_key"],
                schedule_cron=CRON_DAILY_2AM,
                batch_size=100,
                status=PipelineStatus.ACTIVE.value,
                created_at=datetime(2026, 11, 9, 9, 40, tzinfo=timezone.utc),
            )
            db.add(pipeline)
            db.flush()
            _created("SyncPipeline", definition["name"])
        else:
            _skipped("SyncPipeline", definition["name"])

        existing = (
            db.query(FieldMapping).filter(FieldMapping.pipeline_id == pipeline.id).count()
        )
        if existing == 0:
            for index, (source_field, target_column, transform, config, required) in enumerate(
                definition["mappings"]
            ):
                db.add(
                    FieldMapping(
                        pipeline_id=pipeline.id,
                        source_field=source_field,
                        target_column=target_column,
                        transform_type=transform,
                        transform_config_json=config,
                        default_value=None,
                        is_required=required,
                        order_index=index,
                    )
                )
            _created("FieldMapping", f"{definition['name']} ({len(definition['mappings'])})")
        else:
            _skipped("FieldMapping", f"{definition['name']} ({existing})")
    db.commit()


# ---------------------------------------------------------------- 入口 ----


def seed_all() -> dict[str, int]:
    global CREATED, SKIPPED
    CREATED = 0
    SKIPPED = 0

    source_dir = Path(settings.source_dir)
    artifact_dir = Path(settings.artifact_dir)
    csv_path = ensure_file(source_dir, CSV_FILENAME, build_csv_text())
    ensure_file(source_dir, JSONL_FILENAME, build_jsonl_text())
    artifact_dir.mkdir(parents=True, exist_ok=True)

    seed_target_tables()

    with session_scope() as db:
        users = seed_users(db)
        owner = users[ROLE_OWNER]
        sources = seed_sources(db, owner, csv_path, source_dir / JSONL_FILENAME)
        seed_pipelines(db, owner, sources)

    print(f"SEED_SUMMARY created={CREATED} skipped={SKIPPED}", flush=True)
    return {"created": CREATED, "skipped": SKIPPED}


def main() -> int:
    try:
        result = seed_all()
    except Exception as exc:  # noqa: BLE001
        print(f"SEED_FAILED reason={exc}", file=sys.stderr, flush=True)
        return 1
    if result["created"] == 0 and result["skipped"] == 0:
        print("SEED_FAILED reason=nothing happened", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
