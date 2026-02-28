from langchain.agents import create_agent


class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=None,
            system_prompt=None,
            tools=[],
            middleware=[],
        )

    def execute_stream(self, query: str):
        input_dict = {
            "messages": [
                {"role": "user", "content": query}
            ]
        }

        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["message"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"


if __name__ == '__main__':
    agent = ReactAgent()

    query = "here is your question"
    for chunk in agent.execute_stream(query):
        print(chunk, end="", flush=True)
