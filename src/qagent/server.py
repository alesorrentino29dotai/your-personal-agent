import os
import secrets
from pathlib import Path
from typing import Optional

from qagent.agent import Agent

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None


SESSIONS: "dict[str, Agent]" = {}
WEB_DIR = Path(__file__).parent / "web"


if BaseModel is not None:

    class AskBody(BaseModel):
        message: str
        session_id: Optional[str] = None

    class ResetBody(BaseModel):
        session_id: Optional[str] = None
else:
    AskBody = None
    ResetBody = None


def _new_session_id() -> str:
    return secrets.token_urlsafe(16)


def _check_auth(provided: str | None, expected: str | None) -> bool:
    if not expected:
        return True
    if not provided:
        return False
    if provided.startswith("Bearer "):
        provided = provided.removeprefix("Bearer ")
    return secrets.compare_digest(provided, expected)


def build_app(
    *,
    model: str,
    root: Path,
    host: str,
    allow_shell: bool,
    allow_write: bool,
    allow_send: bool,
    max_steps: int,
    api_token: str | None,
):
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="Personal Agent", version="0.3.0")

    def get_or_create(session_id):
        if session_id and session_id in SESSIONS:
            return session_id, SESSIONS[session_id]
        new_id = _new_session_id()
        agent = Agent(
            model=model, root=root, allow_shell=allow_shell,
            allow_write=allow_write, allow_send=allow_send,
            max_steps=max_steps, host=host,
        )
        SESSIONS[new_id] = agent
        return new_id, agent

    @app.get("/api/health")
    def health():
        return {"ok": True, "model": model, "sessions": len(SESSIONS)}

    @app.get("/api/tools")
    def tools(authorization: str | None = None):
        from qagent.tools import ToolRunner
        r = ToolRunner(root, allow_shell=allow_shell,
                       allow_write=allow_write, allow_send=allow_send)
        names = [s["function"]["name"] for s in r.schemas()]
        return {"tools": names, "count": len(names)}

    @app.post("/api/ask")
    async def ask(body: AskBody, request: Request):
        if not _check_auth(request.headers.get("authorization"), api_token):
            raise HTTPException(401, "Unauthorized")
        sid, agent = get_or_create(body.session_id)
        try:
            reply = agent.ask(body.message)
        except Exception as exc:
            raise HTTPException(500, f"Agent error: {exc}")
        return {"session_id": sid, "reply": reply}

    @app.post("/api/reset")
    async def reset(body: ResetBody, request: Request):
        if not _check_auth(request.headers.get("authorization"), api_token):
            raise HTTPException(401, "Unauthorized")
        if body.session_id and body.session_id in SESSIONS:
            SESSIONS[body.session_id].reset()
            return {"ok": True}
        return {"ok": False, "error": "unknown session_id"}

    if WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")

    return app


def run_server(*, host_bind: str = "0.0.0.0", port: int = 8765,
               api_token: str | None = None, **agent_kwargs) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "Server deps not installed. Run: pip install -e '.[server]'"
        ) from exc
    app = build_app(api_token=api_token, **agent_kwargs)
    print(f"Personal Agent listening on http://{host_bind}:{port}")
    print(f"Open in browser, or phone (same WiFi): http://<your-LAN-IP>:{port}")
    if api_token:
        print(f"API token required: send Authorization: Bearer {api_token[:6]}...")
    uvicorn.run(app, host=host_bind, port=port, log_level="info")
