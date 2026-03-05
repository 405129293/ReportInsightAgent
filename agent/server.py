# server.py
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse, StreamingResponse

from agent.react_agent import ReactAgent

app = FastAPI(title="Report/SQL Agent Service")
agent = ReactAgent()


class AskReq(BaseModel):
    query: str
    stream: bool = False


@app.post("/ask")
def ask(req: AskReq):
    """
    外部系统 POST:
    {
      "query": "数据库中ctct_etl_error_message_record表的前10条数据是什么样的?",
      "stream": false
    }
    """
    query = (req.query or "").strip()
    if not query:
        return JSONResponse({"ok": False, "error": "query is empty"}, status_code=400)

    # 1) 非流式：一次性返回
    if not req.stream:
        try:
            answer = agent.execute(query)
            return {"ok": True, "answer": answer}
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    # 2) 流式：边生成边返回（text/plain）
    def gen():
        try:
            for chunk in agent.execute_stream(query):
                yield chunk
        except Exception as e:
            yield f"\n[ERROR] {e}\n"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")