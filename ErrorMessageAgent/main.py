import json
import os
import time
from datetime import datetime, timedelta

from langchain_openai import ChatOpenAI  # 你也可以换通义/本地模型
from langchain_core.runnables import RunnableLambda

from ErrorMessageAgent.prompt import prompt, parser, ErrorAnalysis, build_raw_snippet, Severity
from ErrorMessageAgent.tool import StarRocksClient, BurstCounter, fingerprint

llm = ChatOpenAI(
        model="qwen-max",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
chain = prompt | llm | parser


def notify(fp: str, analysis: ErrorAnalysis, row: dict, burst_cnt: int):
    # 这里替换为企业微信/飞书/钉钉即可
    print("==== ALERT ====")
    print("fingerprint:", fp)
    print("topic/job:", row["sourceTopic"], row.get("jobName"))
    print("class:", analysis.error_class, "sig:", analysis.error_signature)
    print("severity:", analysis.severity, "confidence:", analysis.confidence, "burst_5m:", burst_cnt)
    print("root_cause:", analysis.root_cause)
    print("suggestions:", analysis.suggestions[:3])
    print("===============")


def run_loop(sr: StarRocksClient):
    last_ts = datetime.now() - timedelta(hours=1) # 首次启动从当前开始；也可从“当前-10分钟”回放
    counter = BurstCounter(window_seconds=300)

    while True:
        rows = sr.fetch_new_errors(last_ts=last_ts, batch_size=200)
        if rows:
            # 更新 checkpoint：用本批最后一条的 dbReceiptTime
            last_ts = max(r["dbReceiptTime"] for r in rows if r["dbReceiptTime"] is not None)

        for r in rows:
            raw_snip = build_raw_snippet(r.get("rawData") or "")

            analysis: ErrorAnalysis = chain.invoke({
                "sourceTopic": r["sourceTopic"],
                "jobName": r.get("jobName") or "",
                "errorOccurTime": str(r["errorOccurTime"]),
                "dbReceiptTime": str(r.get("dbReceiptTime")),
                "errorMsg": r.get("errorMsg") or "",
                "raw_snippet": raw_snip,
            })

            fp = fingerprint(r["sourceTopic"], r.get("jobName") or "", analysis.error_class, analysis.error_signature)
            burst_cnt = counter.add(fp, r["dbReceiptTime"] or datetime.now())

            # 简单策略：P0 或 5分钟内同类>20 触发强告警
            should_alert = (analysis.severity == Severity.P0) or (burst_cnt >= 20) or analysis.should_page
            if should_alert | True:
                notify(fp, analysis, r, burst_cnt)

            # TODO：把 analysis + fp + cnt 写入 ctct_etl_error_analysis_record（或ES）
            # TODO：把已处理 currentMessageId 记录到去重表/缓存

        time.sleep(2)  # 轮询间隔


if __name__ == '__main__':
    db_user = "reader"
    db_password = "e~6npfO_3)HS9m"
    db_host = "10.16.160.86"
    db_port = 20003
    db_name = "rp_log_dwd"

    #self.conn = pymysql.connect(host=host, port=port, user=user, password=password, database=db, charset="utf8mb4")

    sr = StarRocksClient(db_host, db_port, db_user, db_password, db_name)
    run_loop(sr)