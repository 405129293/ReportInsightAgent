import hashlib
from collections import defaultdict
from datetime import timedelta
import pymysql
from datetime import datetime


def fingerprint(topic: str, job: str, error_class: str, signature: str) -> str:
    s = f"{topic}|{job or ''}|{error_class}|{signature}"
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

# 简化：内存窗口计数（生产建议用 Redis/StarRocks 表存）
class BurstCounter:
    def __init__(self, window_seconds=300):
        self.window = timedelta(seconds=window_seconds)
        self.events = defaultdict(list)  # fp -> [datetime...]

    def add(self, fp: str, ts: datetime):
        arr = self.events[fp]
        arr.append(ts)
        # 清理窗口外
        cutoff = ts - self.window
        while arr and arr[0] < cutoff:
            arr.pop(0)
        return len(arr)



class StarRocksClient:
    def __init__(self, host, port, user, password, db):
        self.conn = pymysql.connect(host=host, port=port, user=user, password=password, database=db, charset="utf8mb4")

    def fetch_new_errors(self, last_ts: datetime, batch_size: int = 200):
        sql = """
        SELECT currentMessageId, sourceTopic, errorOccurTime, dbReceiptTime, messageId, jobName, rawData, sourceId, kafkaKey, errorMsg
        FROM ctct_etl_error_message_record
        WHERE dbReceiptTime > %s
        ORDER BY dbReceiptTime ASC, errorOccurTime ASC
        LIMIT %s
        """
        with self.conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, (last_ts, batch_size))
            return cur.fetchall()