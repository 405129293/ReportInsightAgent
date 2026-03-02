import os

from langchain_classic.agents import AgentType
from langchain_community.agent_toolkits import SQLDatabaseToolkit, create_sql_agent
from langchain_community.chat_models import ChatOpenAI
from langchain_community.llms.openai import OpenAI
from langchain_community.utilities import SQLDatabase


db_user = "reader"
db_password = "e~6npfO_3)HS9m"
db_host = "10.16.160.86:20003"
db_name = "rp_log_ods"
# db = SQLDatabase.from_uri(f"mysql://{db_user}:{db_password}@{db_host}/{db_name}")
# 或者直接使用
# db = SQLDatabase.from_uri(f"mysql+pymysql://root:Aa123456!@localhost/ecommerce_db")

# @tool(description="连接数据库的示例，查询数据库中数据")
# def link_database_demo(query: str) -> str:
#     return "数据库连接成功，数据库中共有10张表，分别是：表1，表2，表3，表4，表5，表6，表7，表8，表9，表10"
#
#
# @tool(description="连接真实数据库，查询数据库中数据")
# def link_database(query: str) -> str:
#     return "数据库连接成功，数据库中共有10张表，分别是：表1，表2，表3，表4，表5，表6，表7，表8，表9，表10"


# db_user = os.getenv("DB_USER")
# db_password = os.getenv("DB_PASSWORD")
# db_host = os.getenv("DB_HOST")          # 例如: 10.16.160.86:20003
# db_name = os.getenv("DB_NAME")

# db = SQLDatabase.from_uri(f"mysql://{db_user}:{db_password}@{db_host}/{db_name}")

db = SQLDatabase.from_uri(
    f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
)

llm = ChatOpenAI(
    model="qwen-max",  # 按你实际可用模型名改
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

toolkit = SQLDatabaseToolkit(db=db, llm=llm)

ZH_SQL_PREFIX = """
你是一个专业的SQL数据分析师。你需要根据用户的问题，与一个SQL数据库交互，并返回答案。
请全程使用中文。
执行步骤：
1) 先查看有哪些表
2) 必要时查看相关表的schema
3) 生成正确SQL（避免SELECT *；限制返回行数）
4) 执行并基于结果回答
如果无法得到答案，直接说明原因，不要编造。
"""

ZH_SQL_SUFFIX = """
问题：{input}
{agent_scratchpad}
"""

agent_executor = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    prefix=ZH_SQL_PREFIX,
    suffix=ZH_SQL_SUFFIX,
    verbose=True,
    agent_executor_kwargs={"handle_parsing_errors": True},
)

print(agent_executor.invoke({"input": "获取所有表信息"}))