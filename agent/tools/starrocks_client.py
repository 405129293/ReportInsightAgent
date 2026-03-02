import os
import pymysql
from pymysql.connections import Connection

from utils.config_handler import starrocks_conf


class StarRocksClient:
    """
    直连 StarRocks（MySQL 协议）的轻量执行器。
    - 每次执行临时建连接（简单稳定）
    - 支持连接超时/读超时
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        connect_timeout: int = 5,
        read_timeout: int = 30,
        write_timeout: int = 30,
        charset: str = "utf8mb4",
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.charset = charset

    def _connect(self) -> Connection:
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            connect_timeout=self.connect_timeout,
            read_timeout=self.read_timeout,
            write_timeout=self.write_timeout,
            charset=self.charset,
            autocommit=True,
        )

    def query(self, sql: str):
        """返回 (columns, rows)"""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                columns = [d[0] for d in (cur.description or [])]
                return columns, rows
        finally:
            conn.close()


def build_starrocks_client() -> StarRocksClient:
    return StarRocksClient(
        host=starrocks_conf["test"]["db_host"].split(":")[0],
        port=int(starrocks_conf["test"]["db_host"].split(":")[1]),
        user=starrocks_conf["test"]["db_user"],
        password=starrocks_conf["test"]["db_password"],
        database=starrocks_conf["test"]["db_name"],
        connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
        read_timeout=int(os.getenv("DB_READ_TIMEOUT", "30")),
        write_timeout=int(os.getenv("DB_WRITE_TIMEOUT", "30")),
    )