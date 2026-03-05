from langchain.agents import create_agent

from agent.tools.sql_straight_query_tool import sql_straight_query_tool
from agent.tools.agent_tools import link_database
from agent.tools.middleware import monitor_tool, log_before_model
from agent.tools.sql_agent_tool import sql_query_tool
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts


class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            #tools=[sql_query_tool],
            tools=[sql_straight_query_tool],
            middleware=[monitor_tool, log_before_model],
        )

    def execute_stream(self, query: str):
        input_dict = {
            "messages": [
                {"role": "user", "content": query}
            ]
        }

        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"


if __name__ == '__main__':
    agent = ReactAgent()

    query = "数据库中ctct_etl_error_message_record表的前10条数据是什么样的?"
    for chunk in agent.execute_stream(query):
        print(chunk, end="", flush=True)
