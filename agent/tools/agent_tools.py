

from langchain_core.tools import tool

@tool(description="连接数据库的示例，查询数据库中数据")
def link_database(query: str) -> str:
    return "数据库连接成功，数据库中共有10张表，分别是：表1，表2，表3，表4，表5，表6，表7，表8，表9，表10"


