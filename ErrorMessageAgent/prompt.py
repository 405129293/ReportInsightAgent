import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class Severity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"

class ErrorClass(str, Enum):
    INVALID_JSON = "INVALID_JSON"
    MISSING_FIELD = "MISSING_FIELD"
    FUTURE_TIME = "FUTURE_TIME"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    UPSTREAM_DIRTY_DATA = "UPSTREAM_DIRTY_DATA"
    CONFIG_OR_RULE_ERROR = "CONFIG_OR_RULE_ERROR"
    UNKNOWN = "UNKNOWN"

class ErrorAnalysis(BaseModel):
    error_class: ErrorClass
    error_signature: str = Field(description="用于聚合的稳定特征，比如 missing_field=log_type")
    root_cause: str
    evidence: List[str]
    suggestions: List[str]
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    should_page: bool
    tags: List[str]

parser = PydanticOutputParser(pydantic_object=ErrorAnalysis)

SYSTEM_RULES = """你是资深大数据平台异常分析专家，熟悉 Kafka/Flink/StarRocks/ETL清洗。
目标：对异常消息做归因分类、生成可执行修复建议、并给出严重级别与置信度。
要求：
1) 必须输出为指定JSON结构，字段完整。
2) evidence 只能引用输入中的短片段（不要长段复制）。
3) 建议要可落地，尽量贴合：容错解析、字段兼容、时间校验、上游数据治理、回溯修复、监控与限流。
4) 对同类错误要给“稳定可聚合的 error_signature”（例如 invalid_json=message / missing_field=log_type / future_time=collectorReceiptTime）。
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_RULES),
    ("human", """下面是一条实时ETL异常入库记录，请分析：

sourceTopic: {sourceTopic}
jobName: {jobName}
errorOccurTime: {errorOccurTime}
dbReceiptTime: {dbReceiptTime}

errorMsg:
{errorMsg}

rawDataSnippet:
{raw_snippet}

请输出：{format_instructions}
""")
]).partial(format_instructions=parser.get_format_instructions())

def build_raw_snippet(raw: str, head=2000, tail=2000) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    if len(raw) <= head + tail:
        snippet = raw
    else:
        snippet = raw[:head] + "\n...\n" + raw[-tail:]

    # 示例脱敏：IP、tenantNo（你们可以按需要扩展）
    snippet = re.sub(r"\b(\d{1,3}\.){3}\d{1,3}\b", "<IP>", snippet)
    snippet = re.sub(r"tenantNo:\d+", "tenantNo:<MASK>", snippet)
    return snippet