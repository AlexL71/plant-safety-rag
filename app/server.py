"""DocAgent web server (FastAPI).

    python -m app.server            # http://127.0.0.1:8000  (host/port in configs/config.yaml, section web)

Pages: /  (landing) · /chat  (users) · /admin  (password-protected console).
Users are anonymous: a random id in an HttpOnly cookie owns their chats (max `web.max_chats_per_user`).
Answers stream progress as Server-Sent Events while the ~20 s pipeline runs.
"""
from __future__ import annotations

import json
import logging
import os
import queue
import re
import threading
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import auth
from app.engine import SETUP_INFO, Engine
from app.store import VERDICTS, Store
from plant_rag.config import REPO_ROOT, resolve_path

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"
BRAND = REPO_ROOT / "docs" / "brand"
USER_COOKIE, ADMIN_COOKIE = "da_uid", "da_admin"

engine = Engine(os.environ.get("PLANT_RAG_CONFIG"))
cfg, web = engine.cfg, engine.cfg["web"]
store = Store(resolve_path(web["db_path"]))

app = FastAPI(title="DocAgent", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.mount("/brand", StaticFiles(directory=BRAND), name="brand")


# ---------------------------------------------------------------- helpers
def user_id(request: Request, response: Response) -> str:
    """Anonymous user id from the cookie; a new one is issued on first visit."""
    uid = request.cookies.get(USER_COOKIE)
    if not uid or not re.fullmatch(r"[0-9a-f]{32}", uid):
        uid = uuid.uuid4().hex
        response.set_cookie(USER_COOKIE, uid, max_age=365 * 86400, httponly=True, samesite="lax")
    return uid


def admin_user(request: Request) -> str:
    name = store.session_user(request.cookies.get(ADMIN_COOKIE))
    if not name:
        raise HTTPException(401, "Admin login required")
    return name


def user_setup() -> str:
    s = store.get_setting("user_setup", web["default_user_setup"])
    return s if s in cfg["retrieval"]["setups"] else "E"


def public_message(m: dict[str, Any], admin: bool = False) -> dict[str, Any]:
    """What the browser gets for one message. Users see the answer and the passages it cites (for the pop-ups);
    admins also get every passage given to the model, with scores."""
    out = {"id": m["id"], "role": m["role"], "text": m["text"], "created": m["created"]}
    p = m.get("payload")
    if m["role"] != "assistant" or not p:
        return out
    ev = {e["n"]: e for e in p.get("evidence", [])}
    out |= {k: p.get(k) for k in ("lang", "refused", "reason", "standalone", "translated", "total_s", "error")}
    out["passages"] = {str(n): {**(engine.passage(ev[n]["chunk_id"]) or {}), "n": n, "score": ev[n]["score"]}
                       for n in p.get("cited", []) if n in ev}
    if admin:
        out["evidence"] = [{**(engine.passage(e["chunk_id"]) or {}), "n": e["n"], "score": e["score"],
                            "cited": e["n"] in p.get("cited", [])} for e in p.get("evidence", [])]
        out |= {k: p.get(k) for k in ("setup", "threshold", "timings", "llm_s", "llm_cached", "question")}
    return out


def stream_answer(question: str, history: list[tuple[str, str]], setup: str, on_done, on_error=None,
                  answer_lang: str | None = None) -> StreamingResponse:
    """Run the pipeline in a worker thread and stream its stages as Server-Sent Events."""
    q: queue.Queue = queue.Queue()

    def worker() -> None:
        try:
            res = engine.run(question, history, setup, on_stage=lambda s: q.put({"type": "stage", "stage": s}),
                             answer_lang=answer_lang)
            q.put({"type": "done", "message": on_done(res)})
        except Exception as exc:  # reported to the browser; details in the server log
            log.exception("Answering failed")
            detail = str(exc) if isinstance(exc, RuntimeError) else \
                f"Something went wrong ({type(exc).__name__}). Please try again."
            if on_error:
                on_error(detail)
            q.put({"type": "error", "detail": detail})
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def events():
        while (item := q.get()) is not None:
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class AskBody(BaseModel):
    question: str = Field(min_length=1)
    lang: Literal["auto", "ko", "en"] = "auto"  # answer language; "auto" = same as the question


class AdminAskBody(BaseModel):
    question: str = Field(min_length=1)
    setup: str = "E"


class LoginBody(BaseModel):
    username: str
    password: str


class ReviewBody(BaseModel):
    verdict: str
    note: str = ""


class SettingsBody(BaseModel):
    user_setup: str


# ---------------------------------------------------------------- pages
@app.get("/", include_in_schema=False)
def landing() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/chat", include_in_schema=False)
def chat_page() -> FileResponse:
    return FileResponse(STATIC / "chat.html")


@app.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(STATIC / "admin.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(BRAND / "docagent_icon.svg", media_type="image/svg+xml")


# ---------------------------------------------------------------- public API
@app.get("/api/status")
def status() -> dict[str, Any]:
    return engine.status() | {"limits": {k: web[k] for k in ("max_chats_per_user", "max_turns_per_chat",
                                                            "max_question_chars")}}


@app.get("/api/chats")
def list_chats(uid: str = Depends(user_id)) -> dict[str, Any]:
    return {"chats": store.list_chats(uid), "max": web["max_chats_per_user"]}


@app.post("/api/chats")
def new_chat(uid: str = Depends(user_id)) -> dict[str, Any]:
    return store.create_chat(uid, int(web["max_chats_per_user"]))


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str, uid: str = Depends(user_id)) -> dict[str, Any]:
    chat = store.get_chat(chat_id, uid)
    if not chat:
        raise HTTPException(404, "Chat not found")
    return {"chat": chat, "messages": [public_message(m) for m in store.messages(chat_id)]}


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str, uid: str = Depends(user_id)) -> dict[str, Any]:
    store.delete_chat(chat_id, uid)
    return {"ok": True}


@app.post("/api/chats/{chat_id}/ask")
def ask(chat_id: str, body: AskBody, uid: str = Depends(user_id)) -> StreamingResponse:
    chat = store.get_chat(chat_id, uid)
    if not chat:
        raise HTTPException(404, "Chat not found")
    question = body.question.strip()
    if len(question) > int(web["max_question_chars"]):
        raise HTTPException(413, f"Question too long (max {web['max_question_chars']} characters)")
    if store.count_turns(chat_id) >= int(web["max_turns_per_chat"]):
        raise HTTPException(409, "This chat is full. Please start a new chat.")
    if not engine.ready:
        raise HTTPException(503, engine.error or "DocAgent is starting up. Please try again in a few seconds.")
    history = store.history(chat_id)
    store.add_message(chat_id, "user", question)
    store.touch_chat(chat_id, title=question[:70] if not history else None)

    def on_done(res: dict[str, Any]) -> dict[str, Any]:
        mid = store.add_message(chat_id, "assistant", res["text"], res)
        store.touch_chat(chat_id)
        return public_message({"id": mid, "role": "assistant", "text": res["text"], "created": 0, "payload": res})

    def on_error(detail: str) -> None:  # keep the chat consistent: every question gets a reply
        store.add_message(chat_id, "assistant", detail, {"error": True, "refused": True, "reason": "error"})

    return stream_answer(question, history, user_setup(), on_done, on_error,
                         answer_lang=None if body.lang == "auto" else body.lang)


@app.get("/api/passages/{chunk_id}")
def passage(chunk_id: str) -> dict[str, Any]:
    p = engine.passage(chunk_id, with_boxes=True)
    if not p:
        raise HTTPException(404, "Passage not found")
    return p


@app.get("/api/docs/{doc_id}")
def doc_meta(doc_id: str) -> dict[str, Any]:
    d = engine.docs.get(doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    return {k: d[k] for k in ("doc_id", "title", "lang", "pages")}


@app.get("/api/docs/{doc_id}/pages/{page}.png")
def page_image(doc_id: str, page: int) -> FileResponse:
    if doc_id not in engine.docs:
        raise HTTPException(404, "Document not found")
    try:
        path = engine.page_png(doc_id, page)
    except IndexError:
        raise HTTPException(404, "Page not found") from None
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


# ---------------------------------------------------------------- admin API
@app.post("/api/admin/login")
def login(body: LoginBody, response: Response) -> dict[str, Any]:
    if not auth.load_credentials(cfg):
        raise HTTPException(503, "No admin account yet. Create one with: python -m app.auth --username admin")
    if not auth.verify(cfg, body.username, body.password):
        raise HTTPException(401, "Wrong username or password")
    token = store.new_session(body.username, float(web["admin_session_hours"]))
    response.set_cookie(ADMIN_COOKIE, token, max_age=int(float(web["admin_session_hours"]) * 3600),
                        httponly=True, samesite="strict")
    return {"username": body.username}


@app.post("/api/admin/logout")
def logout(request: Request, response: Response) -> dict[str, Any]:
    store.end_session(request.cookies.get(ADMIN_COOKIE))
    response.delete_cookie(ADMIN_COOKIE)
    return {"ok": True}


@app.get("/api/admin/me")
def me(name: str = Depends(admin_user)) -> dict[str, Any]:
    return {"username": name}


@app.get("/api/admin/overview")
def overview(_: str = Depends(admin_user)) -> dict[str, Any]:
    return {"stats": store.stats(), "status": engine.status(), "user_setup": user_setup()}


@app.get("/api/admin/settings")
def get_settings(_: str = Depends(admin_user)) -> dict[str, Any]:
    return {"user_setup": user_setup(), "setups": SETUP_INFO,
            "limits": {k: web[k] for k in ("max_chats_per_user", "max_turns_per_chat", "max_question_chars")}}


@app.put("/api/admin/settings")
def put_settings(body: SettingsBody, _: str = Depends(admin_user)) -> dict[str, Any]:
    if body.user_setup not in SETUP_INFO:
        raise HTTPException(422, "Unknown setup")
    store.set_setting("user_setup", body.user_setup)
    return {"user_setup": body.user_setup}


@app.get("/api/admin/answers")
def answers(limit: int = 50, offset: int = 0, verdict: str | None = None, _: str = Depends(admin_user)) -> dict:
    rows = store.list_answers(min(limit, 200), max(offset, 0), verdict)
    return {"answers": [{"id": r["id"], "question": r["question"], "text": r["text"], "created": r["created"],
                         "verdict": r["verdict"], "refused": (r["payload"] or {}).get("refused"),
                         "setup": (r["payload"] or {}).get("setup")} for r in rows]}


@app.get("/api/admin/answers/{message_id}")
def answer_detail(message_id: int, _: str = Depends(admin_user)) -> dict[str, Any]:
    r = store.get_answer(message_id)
    if not r:
        raise HTTPException(404, "Answer not found")
    msg = public_message({"id": r["id"], "role": "assistant", "text": r["text"], "created": r["created"],
                          "payload": r["payload"]}, admin=True)
    return msg | {"question": r["question"], "review": {"verdict": r["verdict"], "note": r["note"],
                                                       "reviewer": r["reviewer"], "updated": r["reviewed"]}}


@app.put("/api/admin/answers/{message_id}/review")
def review(message_id: int, body: ReviewBody, name: str = Depends(admin_user)) -> dict[str, Any]:
    if body.verdict not in VERDICTS:
        raise HTTPException(422, f"verdict must be one of {sorted(VERDICTS)}")
    if not store.get_answer(message_id):
        raise HTTPException(404, "Answer not found")
    store.set_review(message_id, body.verdict, body.note[:2000], name)
    return {"ok": True}


@app.post("/api/admin/ask")
def admin_ask(body: AdminAskBody, _: str = Depends(admin_user)) -> StreamingResponse:
    if body.setup not in SETUP_INFO:
        raise HTTPException(422, "Unknown setup")
    if not engine.ready:
        raise HTTPException(503, engine.error or "DocAgent is starting up.")

    def on_done(res: dict[str, Any]) -> dict[str, Any]:
        return public_message({"id": 0, "role": "assistant", "text": res["text"], "created": 0, "payload": res},
                              admin=True)

    return stream_answer(body.question.strip()[: int(web["max_question_chars"])], [], body.setup, on_done)


@app.get("/api/admin/docs")
def admin_docs(_: str = Depends(admin_user)) -> dict[str, Any]:
    return {"docs": [{k: d.get(k) for k in ("doc_id", "title", "lang", "source_url", "chunks")} | {"n_pages": len(d["pages"])}
                     for d in engine.docs.values()]}


@app.get("/api/admin/docs/{doc_id}/file")
def admin_doc_file(doc_id: str, _: str = Depends(admin_user)) -> FileResponse:
    d = engine.docs.get(doc_id)
    if not d:
        raise HTTPException(404, "Document not found")
    return FileResponse(d["file"], media_type="application/pdf", filename=Path(d["file"]).name,
                        content_disposition_type="inline")


@app.get("/api/admin/docs/{doc_id}/clauses")
def admin_doc_clauses(doc_id: str, _: str = Depends(admin_user)) -> dict[str, Any]:
    if doc_id not in engine.docs:
        raise HTTPException(404, "Document not found")
    return {"clauses": [{"chunk_id": c["chunk_id"], "clause_id": c["clause_id"], "page_start": c["page_start"]}
                        for c in engine.chunks.values() if c["doc_id"] == doc_id]}


@app.exception_handler(HTTPException)
def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("httpx", "google_genai", "huggingface_hub", "transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    uvicorn.run(app, host=web["host"], port=int(web["port"]), log_level="warning")


if __name__ == "__main__":
    main()
