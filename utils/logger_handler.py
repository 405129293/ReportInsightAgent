import logging
import os
from datetime import datetime

from utils.path_tool import get_abs_path

LOG_ROOT = get_abs_path("logs")

os.makedirs(LOG_ROOT, exist_ok=True)

DEFAULT_LOG_FORMAT = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)


def get_logger(
        name: str = "agent",
        console_level: int = logging.INFO,  # 定义控制台能输出日志级别
        file_level: int = logging.DEBUG,  # 文件最低写入级别
        log_file=None,  # 你可手动指定日志文件路径；不指定则按默认规则生成
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    """
    logging.getLogger(name) 返回的是全局单例（按 name 缓存）。
    如果多个文件/多次调用 get_logger()，每次都 addHandler，就会出现：
    同一条日志在控制台打印 N 次，文件里也重复 N 次
    所以这里判断来只在第一次创建时加 handler，后续直接复用。
    """
    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(DEFAULT_LOG_FORMAT)

    logger.addHandler(console_handler)

    if not log_file:
        """
        如果没传 log_file：
        文件名类似：logs/agent_20260212.log
        按天分文件（每天一个）
        """
        log_file = os.path.join(LOG_ROOT, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(DEFAULT_LOG_FORMAT)

    logger.addHandler(file_handler)

    return logger


logger = get_logger()

if __name__ == '__main__':
    logger.info("信息日志")
    logger.error("错误日志")
    logger.warning("警告日志")
    logger.debug("调试日志")
