"""导出 MySQL 8 建表 SQL（sql/schema.sql）与测试数据（sql/data.sql）。

用法（在 backend 目录下执行）：
    py -3.12 -m scripts.export_schema_sql
或：
    py -3.12 scripts/export_schema_sql.py

说明：
- schema.sql 由 SQLAlchemy 模型元数据按 MySQL 方言编译生成，含 DROP TABLE IF EXISTS。
- data.sql 从当前连接的数据库读取全部数据行，生成可重复执行的 INSERT 语句
  （执行前会清空各表，便于重置演示环境）。
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

# 允许以脚本方式直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.dialects import mysql  # noqa: E402
from sqlalchemy.schema import CreateTable  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app.models import Base  # noqa: E402  （导入包即注册所有表）

SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"
DB_NAME = engine.url.database or "scheduling"

HEADER = """-- =====================================================================
--  车辆智能调度 Agent —— MySQL 8 数据库脚本
--  数据库：{db}
--  字符集：utf8mb4 / utf8mb4_general_ci
--  由 backend/scripts/export_schema_sql.py 自动生成，请勿手工修改
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `{db}`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_general_ci;

USE `{db}`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
"""

FOOTER = """
SET FOREIGN_KEY_CHECKS = 1;
"""


def _lit(value) -> str:
    """把 Python 值转成 MySQL 字面量。"""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
        return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if isinstance(value, datetime):
        return "'" + value.strftime("%Y-%m-%d %H:%M:%S") + "'"
    if isinstance(value, date):
        return "'" + value.isoformat() + "'"
    text = str(value)
    text = text.replace("\\", "\\\\").replace("'", "\\'")
    return "'" + text + "'"


def build_schema_sql() -> str:
    dialect = mysql.dialect()
    lines = [HEADER.format(db=DB_NAME)]
    for table in reversed(Base.metadata.sorted_tables):
        lines.append(f"DROP TABLE IF EXISTS `{table.name}`;")
    lines.append("")
    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=dialect)).strip()
        lines.append(f"-- ---------- {table.name} ----------")
        lines.append(ddl + ";")
        lines.append("")
    lines.append(FOOTER)
    return "\n".join(lines)


def build_data_sql() -> str:
    lines = [HEADER.format(db=DB_NAME)]
    lines.append("-- 清空旧数据（按依赖倒序）")
    for table in reversed(Base.metadata.sorted_tables):
        lines.append(f"DELETE FROM `{table.name}`;")
    lines.append("")

    total = 0
    with SessionLocal() as db:
        for table in Base.metadata.sorted_tables:
            rows = list(db.execute(select(table)).mappings())
            if not rows:
                continue
            lines.append(f"-- ---------- {table.name}（{len(rows)} 行） ----------")
            cols = [c.name for c in table.columns]
            col_list = ", ".join(f"`{c}`" for c in cols)
            for row in rows:
                values = ", ".join(_lit(row[c]) for c in cols)
                lines.append(f"INSERT INTO `{table.name}` ({col_list}) VALUES ({values});")
            lines.append("")
            total += len(rows)

    lines.append(FOOTER)
    lines.append(f"-- 共导出 {total} 行测试数据")
    return "\n".join(lines)


def main() -> None:
    SQL_DIR.mkdir(parents=True, exist_ok=True)

    schema_path = SQL_DIR / "schema.sql"
    schema_path.write_text(build_schema_sql(), encoding="utf-8")
    print(f"已生成 {schema_path}（{len(Base.metadata.sorted_tables)} 张表）")

    data_path = SQL_DIR / "data.sql"
    data_path.write_text(build_data_sql(), encoding="utf-8")
    print(f"已生成 {data_path}")


if __name__ == "__main__":
    main()