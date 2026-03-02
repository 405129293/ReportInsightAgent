from langchain_classic.agents import AgentType
from langchain_community.agent_toolkits import SQLDatabaseToolkit, create_sql_agent
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
import os

db_user = "reader"
db_password = "e~6npfO_3)HS9m"
db_host = "10.16.160.86:20003"
db_name = "rp_log_ods"


def build_sql_agent():
    db = SQLDatabase.from_uri(
        f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}",
        include_tables=[
            "ctct_antideface_fcg_lm_ods",
            # 只加你会查的表
        ],
    )

    llm = ChatOpenAI(
        model="qwen-max",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,  # 为True时打印 Thought/Action/Observation
        agent_executor_kwargs={"handle_parsing_errors": True},
    )

    return agent
