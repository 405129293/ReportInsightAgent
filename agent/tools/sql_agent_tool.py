import time
import warnings

from langchain_core.tools import tool
from sqlalchemy.exc import SAWarning

from agent.sql_agent.sql_agent_factory import build_sql_agent
from utils.logger_handler import logger

warnings.filterwarnings("ignore", category=SAWarning)

sql_agent_executor = build_sql_agent()


@tool(description="用于数据库查询和数据分析的问题")
def sql_query_tool(query: str) -> str:
    t0 = time.time()
    logger.info(f"[sql_query_tool] start, query={query!r}")

    # 1) 进入 invoke 之前
    t1 = time.time()
    logger.info(f"[sql_query_tool] before invoke, dt={t1 - t0:.3f}s")

    result = sql_agent_executor.invoke({"input": query})

    # 2) invoke 返回之后
    t2 = time.time()
    logger.info(f"[sql_query_tool] after invoke, dt={t2 - t1:.3f}s, result_type={type(result)}")

    output = result.get("output") if isinstance(result, dict) else str(result)
    logger.info(f"[sql_query_tool] done, output_len={len(output) if output else 0}")

    return output or ""
