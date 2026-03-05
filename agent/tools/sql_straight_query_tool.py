import re
from typing import List, Tuple, Any

from langchain_core.tools import tool
from utils.logger_handler import logger
from agent.tools.starrocks_client import build_starrocks_client

# 全局单例 client：避免每次 tool 调用都创建配置对象
_sr_client = build_starrocks_client()

# 允许的 SQL 开头（只读/只查元数据）
_ALLOWED_PREFIX = (
    "select",
    "show",
    "describe",
    "desc",
    "explain",
)

# 禁止的关键字（简单但非常有效）
_FORBIDDEN_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|truncate|alter|create|grant|revoke|set|use)\b",
    re.IGNORECASE,
)


def _normalize_sql(sql: str) -> str:
    return sql.strip().rstrip(";").strip()


def _is_safe_sql(sql: str) -> bool:
    s = _normalize_sql(sql).lower()
    if not s:
        return False
    if _FORBIDDEN_PATTERN.search(s):
        return False
    return s.startswith(_ALLOWED_PREFIX)


def _ensure_limit(sql: str, default_limit: int = 50, max_limit: int = 200) -> str:
    """
    1) 没有 LIMIT：自动加默认 LIMIT
    2) 有 LIMIT：限制最大 LIMIT
    """
    s = _normalize_sql(sql)

    # 只对 SELECT 自动加 limit（SHOW/DESC 不需要）
    if not s.lower().startswith("select"):
        return s + ";"

    # 查找 LIMIT
    m = re.search(r"\blimit\s+(\d+)\b", s, flags=re.IGNORECASE)
    if not m:
        return s + f" LIMIT {default_limit};"

    n = int(m.group(1))
    if n > max_limit:
        # 替换成 max_limit
        s = re.sub(r"\blimit\s+\d+\b", f"LIMIT {max_limit}", s, flags=re.IGNORECASE)

    return s + ";"


def _format_table(columns: List[str], rows: Tuple[Tuple[Any, ...], ...], max_chars: int = 40000) -> str:
    """
    把查询结果格式化成“文本表格”，并限制最大字符数，避免塞爆大模型。
    """
    if not columns:
        return "（无返回列）"
    if not rows:
        return "（查询成功，但结果为空）"

    # 将所有值转成 str，避免 datetime/decimal 等
    str_rows = []
    for r in rows:
        str_rows.append([("" if v is None else str(v)) for v in r])

    # 简单表格：用 tab 分隔
    lines = []
    lines.append("\t".join(columns))
    for r in str_rows:
        lines.append("\t".join(r))

    out = "\n".join(lines)

    if len(out) > max_chars:
        out = out[:max_chars] + "\n...（结果过长已截断）"
    return out


@tool(description="直连 StarRocks 执行只读 SQL（SELECT/SHOW/DESC/EXPLAIN）。参数：query 为 SQL 字符串。")
def sql_straight_query_tool(query: str) -> str:
    """
    这是“纯执行器”tool：只负责执行 SQL 并返回结果文本，不做二次 Agent 推理。
    """
    sql = _normalize_sql(query)

    logger.info(f"[sql_query_tool] incoming sql={sql!r}")

    if not _is_safe_sql(sql):
        return "拒绝执行：仅允许 SELECT/SHOW/DESC/EXPLAIN 等只读 SQL，且禁止 DDL/DML（insert/update/delete/drop/alter/create 等）。"

    # 自动补 limit，避免一次拉太多数据
    sql = _ensure_limit(sql, default_limit=50, max_limit=200)
    logger.info(f"[sql_query_tool] final sql={sql!r}")

    try:
        cols, rows = _sr_client.query(sql)
        logger.info(f"[sql_query_tool] ok, rows={len(rows)}")
        return _format_table(cols, rows, max_chars=40000)
    except Exception as e:
        logger.exception(f"[sql_query_tool] failed: {e}")
        return f"SQL 执行失败：{type(e).__name__}: {e}"
