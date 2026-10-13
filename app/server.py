"""SafetyAgent web server (FastAPI).

    python -m app.server            # http://127.0.0.1:8000  (host/port in configs/config.yaml, section web)

Pages: /  (landing) · /chat  (users) · /notices  (notice editor) · /notice/<id>  (print / share view)
       · /admin  (password-protected console).
Users are anonymous: a random id in an HttpOnly cookie owns their chats and notices.
Long requests (answers, task plans, notices) stream their progress as Server-Sent Events.
"""
from __future__ import annotations

import json
import logging
import os
import queue
import re
import threading
import io
import uuid
from pathlib import Path
from typing import Any, Callable, Literal

import segno

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import auth
from app.engine import SETUP_INFO, Engine
from app.store import NOTICE_STATUSES, VERDICTS, Store
from plant_rag.agent import _visual_cites
from plant_rag.checks import check_elements
from plant_rag.config import REPO_ROOT, resolve_path
from plant_rag.notices import NOTICE_LANGS
from plant_rag.visuals import VISUAL_TYPES

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"
BRAND = REPO_ROOT / "docs" / "brand"
USER_COOKIE, ADMIN_COOKIE = "da_uid", "da_admin"

engine = Engine(os.environ.get("PLANT_RAG_CONFIG"))
cfg, web = engine.cfg, engine.cfg["web"]
store = Store(resolve_path(web["db_path"]))

app = FastAPI(title="SafetyAgent", docs_url=None, redoc_url=None, openapi_url=None)
MODES = [m for m in web.get("modes", ["auto"]) if m in ("auto", "answer", "visual", "compare", "task_plan", "notice")]
TEMPLATES = ("poster", "leaflet", "card", "tbm")
PUBLIC_BASE = str(web.get("public_base_url", "http://127.0.0.1:8000")).rstrip("/")
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
    out |= {k: p.get(k) for k in ("lang", "refused", "reason", "standalone", "translated", "total_s", "error",
                                  "kind", "intent", "visual", "plan", "notice_id", "hazards_searched")}
    out["kind"] = out.get("kind") or "answer"
    out["route_reason"] = (p.get("route") or {}).get("reason")
    out["passages"] = {str(n): {**(engine.passage(ev[n]["chunk_id"]) or {}), "n": n, "score": ev[n]["score"]}
                       for n in p.get("cited", []) if n in ev}
    if admin:
        out["evidence"] = [{**(engine.passage(e["chunk_id"]) or {}), "n": e["n"], "score": e["score"],
                            "cited": e["n"] in p.get("cited", [])} for e in p.get("evidence", [])]
        out |= {k: p.get(k) for k in ("setup", "threshold", "timings", "llm_s", "llm_cached", "question", "route",
                                      "mode", "visual_check", "visual_reason", "plan_check", "notice_check")}
    return out


def sse(work: Callable[[Callable[[str], None]], dict[str, Any]], on_error: Callable[[str], None] | None = None,
        what: str = "Request") -> StreamingResponse:
    """Run `work(stage)` in a worker thread and stream {"type": "stage"} events, then {"type": "done", ...}."""
    q: queue.Queue = queue.Queue()

    def worker() -> None:
        try:
            q.put({"type": "done"} | work(lambda s: q.put({"type": "stage", "stage": s})))
        except Exception as exc:  # reported to the browser; details in the server log
            log.exception("%s failed", what)
            detail = str(exc) if isinstance(exc, (RuntimeError, ValueError)) else \
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


def stream_answer(question: str, history: list[tuple[str, str]], setup: str, on_done, on_error=None,
                  answer_lang: str | None = None, mode: str = "auto") -> StreamingResponse:
    """Run the agent in a worker thread and stream its stages as Server-Sent Events."""
    def work(stage: Callable[[str], None]) -> dict[str, Any]:
        res = engine.run(question, history, setup, on_stage=stage, answer_lang=answer_lang, mode=mode)
        return {"message": on_done(res)}

    return sse(work, on_error, "Answering")


class AskBody(BaseModel):
    question: str = Field(min_length=1)
    lang: Literal["auto", "ko", "en"] = "auto"  # answer language; "auto" = same as the question
    mode: str = "auto"                          # auto (the agent decides) or answer/visual/compare/task_plan/notice


class AdminAskBody(BaseModel):
    question: str = Field(min_length=1)
    setup: str = "E"
    mode: str = "auto"


class VisualBody(BaseModel):
    type: str = "auto"


class NoticeCreateBody(BaseModel):
    topic: str = ""
    message_id: int | None = None
    lang: Literal["ko", "en"] = "ko"
    template: str = "poster"


class NoticeEditBody(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    template: str = "poster"
    main: dict[str, Any]


class TemplateBody(BaseModel):
    template: str


class TranslateBody(BaseModel):
    lang2: str


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


@app.get("/notices", include_in_schema=False)
def notices_page() -> FileResponse:
    return FileResponse(STATIC / "notices.html")


@app.get("/notice/{notice_id}", include_in_schema=False)
def notice_view_page(notice_id: str) -> FileResponse:
    return FileResponse(STATIC / "notice_view.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(BRAND / "safetyagent_icon.svg", media_type="image/svg+xml")


# ---------------------------------------------------------------- public API
@app.get("/api/status")
def status() -> dict[str, Any]:
    return engine.status() | {"limits": {k: web[k] for k in ("max_chats_per_user", "max_turns_per_chat",
                                                            "max_question_chars")},
                              "modes": MODES, "notice_langs": NOTICE_LANGS, "templates": TEMPLATES}


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
        raise HTTPException(503, engine.error or "SafetyAgent is starting up. Please try again in a few seconds.")
    if body.mode not in MODES:
        raise HTTPException(422, f"mode must be one of {MODES}")
    history = store.history(chat_id)
    store.add_message(chat_id, "user", question)
    store.touch_chat(chat_id, title=question[:70] if not history else None)

    def on_done(res: dict[str, Any]) -> dict[str, Any]:
        content = res.pop("notice_content", None)
        mid = store.add_message(chat_id, "assistant", res["text"], res)
        if res.get("kind") == "notice" and content:  # the agent drafted a notice: store it for the editor
            n = store.create_notice(uid, content["title"], res["lang"], "poster",
                                    {"main": content, "evidence": res["evidence"], "check": res.get("notice_check", {}),
                                     "topic": res.get("standalone") or question},
                                    mid, int(web.get("max_notices_per_user", 50)))
            res["notice_id"] = n["id"]
            store.update_payload(mid, res)
        store.touch_chat(chat_id)
        return public_message({"id": mid, "role": "assistant", "text": res["text"], "created": 0, "payload": res})

    def on_error(detail: str) -> None:  # keep the chat consistent: every question gets a reply
        store.add_message(chat_id, "assistant", detail, {"error": True, "refused": True, "reason": "error"})

    return stream_answer(question, history, user_setup(), on_done, on_error,
                         answer_lang=None if body.lang == "auto" else body.lang, mode=body.mode)


@app.post("/api/messages/{message_id}/visual")
def message_visual(message_id: int, body: VisualBody, uid: str = Depends(user_id)) -> dict[str, Any]:
    """Explain an existing answer as a visual, from the same evidence (no new search, one model call)."""
    m = store.get_message(message_id, uid)
    if not m or m["role"] != "assistant" or not m["payload"] or m["payload"].get("refused") \
            or not m["payload"].get("evidence"):
        raise HTTPException(404, "Answer not found")
    if not engine.ready:
        raise HTTPException(503, "SafetyAgent is starting up.")
    payload = m["payload"]
    res = engine.visual_for(payload, body.type if body.type in VISUAL_TYPES else None)
    if not res["visual"]:
        raise HTTPException(422, f"No visual could be made from these sources ({res['reason']}).")
    payload |= {"visual": res["visual"], "visual_check": res["check"], "visual_reason": ""}
    payload["cited"] = sorted(set(payload.get("cited", [])) | _visual_cites(res["visual"]))
    store.update_payload(message_id, payload)
    return public_message({**m, "payload": payload})


# ---------------------------------------------------------------- safety notices
def _notice_passages(content: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Cited evidence numbers -> passage metadata (no full text: the notice shows sources, not clauses)."""
    ev = {e["n"]: e for e in content.get("evidence", [])}
    nums: set[int] = set()
    for key, val in (content.get("main") or {}).items():
        if isinstance(val, list):
            for x in val:
                if isinstance(x, dict):
                    nums.update(c for c in x.get("cite") or [] if isinstance(c, int))
    out = {}
    for n in sorted(nums):
        if n in ev and (p := engine.passage(ev[n]["chunk_id"])):
            out[str(n)] = {k: p[k] for k in ("chunk_id", "doc_id", "title", "clause_id", "page_start", "page_end",
                                             "lang")} | {"n": n}
    return out


NOTICE_LISTS = ("key_rules", "dos", "donts", "permits", "ppe", "tbm_script")


def _notice_warnings(content: dict[str, Any]) -> list[dict[str, Any]]:
    """Numbers guard on the current (possibly hand-edited) text: lines whose numbers are not in the cited source."""
    ev = {e["n"]: e for e in content.get("evidence", [])}
    passages = {n: engine.chunks[e["chunk_id"]] for n, e in ev.items() if e["chunk_id"] in engine.chunks}
    main, warnings = content.get("main") or {}, []
    for key in (*NOTICE_LISTS, "key_numbers"):
        fields = ("label", "value") if key == "key_numbers" else ("text",)
        for i, item in enumerate(main.get(key) or []):
            res = check_elements([item], fields, passages)
            if res.dropped:
                d = res.dropped[0]
                warnings.append({"list": key, "index": i, "reason": d["reason"], "numbers": d.get("numbers", [])})
    return warnings


def public_notice(n: dict[str, Any], can_edit: bool) -> dict[str, Any]:
    c = n["content"]
    return {k: n[k] for k in ("id", "title", "lang", "template", "status", "version", "approved_by", "approved_at",
                              "approved_version", "created", "updated")} | {
        "main": c.get("main"), "translation": c.get("translation"), "line_checks": c.get("line_checks", []),
        "translation_ok": c.get("translation_ok"), "topic": c.get("topic", ""), "check": c.get("check", {}),
        "passages": _notice_passages(c), "warnings": _notice_warnings(c) if can_edit else [],
        "can_edit": can_edit, "share_url": f"{PUBLIC_BASE}/notice/{n['id']}",
        "langs": NOTICE_LANGS, "templates": TEMPLATES,
    }


def _owned_notice(notice_id: str, uid: str) -> dict[str, Any]:
    n = store.get_notice(notice_id)
    if not n or n["user_id"] != uid:
        raise HTTPException(404, "Notice not found")
    return n


def _plan_to_notice(plan: dict[str, Any]) -> dict[str, Any]:
    """A task plan becomes a TBM sheet: controls per hazard as key rules, checks as "do" lines."""
    rules = [{"text": f"{h['hazard']}: {c['text']}", "cite": c["cite"]} for h in plan.get("hazards", [])
             for c in h["controls"]]
    return {"title": plan["title"][:60], "subtitle": "TBM", "key_rules": rules, "dos": plan.get("before_start", []),
            "donts": [], "key_numbers": [], "permits": plan.get("permits", []), "ppe": plan.get("ppe", []),
            "tbm_script": plan.get("tbm_script", [])}


@app.get("/api/notices")
def list_notices(uid: str = Depends(user_id)) -> dict[str, Any]:
    return {"notices": store.list_notices(uid), "max": web.get("max_notices_per_user", 50)}


@app.post("/api/notices")
def create_notice(body: NoticeCreateBody, uid: str = Depends(user_id)) -> StreamingResponse:
    """Draft a notice from a topic (search first) or from a chat answer / plan (reuse its evidence). Streams progress."""
    template = body.template if body.template in TEMPLATES else "poster"
    m = store.get_message(body.message_id, uid) if body.message_id else None
    if body.message_id and (not m or not m["payload"]):
        raise HTTPException(404, "Message not found")
    topic = body.topic.strip()[: int(web["max_question_chars"])]
    if not m and not topic:
        raise HTTPException(422, "Give a topic or a message")
    if not engine.ready:
        raise HTTPException(503, "SafetyAgent is starting up.")

    def work(stage: Callable[[str], None]) -> dict[str, Any]:
        p = m["payload"] if m else {}
        lang = p.get("lang", body.lang) if m else body.lang
        if p.get("kind") == "plan" and p.get("plan"):
            content, check, evidence = _plan_to_notice(p["plan"]), p.get("plan_check", {}), p["evidence"]
            tpl = "tbm"
        else:
            res = engine.notice_from(p.get("standalone") or p.get("question") or topic, lang,
                                     evidence=p.get("evidence") if m else None, setup=user_setup(), on_stage=stage)
            if not res["content"]:
                raise ValueError("The documents don't contain enough rules for this topic to make a notice.")
            content, check, evidence, tpl = res["content"], res["check"], res["evidence"], template
        content["lang"] = lang
        n = store.create_notice(uid, content["title"], lang, tpl,
                                {"main": content, "evidence": evidence, "check": check,
                                 "topic": p.get("standalone") or p.get("question") or topic},
                                body.message_id, int(web.get("max_notices_per_user", 50)))
        return {"notice": public_notice(n, True)}

    return sse(work, None, "Notice")


@app.get("/api/notices/{notice_id}")
def get_notice(notice_id: str, request: Request, uid: str = Depends(user_id)) -> dict[str, Any]:
    """Owner and admins see drafts; anyone with the link sees an approved notice (read-only)."""
    n = store.get_notice(notice_id)
    if not n:
        raise HTTPException(404, "Notice not found")
    is_admin = store.session_user(request.cookies.get(ADMIN_COOKIE)) is not None
    owner = n["user_id"] == uid
    if not (owner or is_admin or n["status"] == "approved"):
        raise HTTPException(404, "Notice not found")
    return public_notice(n, can_edit=owner)


@app.put("/api/notices/{notice_id}")
def edit_notice(notice_id: str, body: NoticeEditBody, uid: str = Depends(user_id)) -> dict[str, Any]:
    n = _owned_notice(notice_id, uid)
    main = {**n["content"]["main"], **{k: v for k, v in body.main.items()
                                        if k in (*NOTICE_LISTS, "key_numbers", "title", "subtitle")}}
    main["title"] = body.title
    content = {**n["content"], "main": main, "translation": None, "line_checks": [], "translation_ok": None}
    return public_notice(store.update_notice(notice_id, body.title, body.template if body.template in TEMPLATES
                                             else n["template"], content), True)


@app.put("/api/notices/{notice_id}/template")
def notice_template(notice_id: str, body: TemplateBody, uid: str = Depends(user_id)) -> dict[str, Any]:
    _owned_notice(notice_id, uid)
    if body.template not in TEMPLATES:
        raise HTTPException(422, "Unknown template")
    store.set_notice_template(notice_id, body.template)
    return public_notice(store.get_notice(notice_id), True)


@app.post("/api/notices/{notice_id}/translate")
def translate_notice(notice_id: str, body: TranslateBody, uid: str = Depends(user_id)) -> dict[str, Any]:
    n = _owned_notice(notice_id, uid)
    if body.lang2 == "none":
        content = {**n["content"], "translation": None, "line_checks": [], "translation_ok": None}
    else:
        if body.lang2 not in NOTICE_LANGS or body.lang2 == n["lang"]:
            raise HTTPException(422, "Pick a second language different from the notice language")
        res = engine.translate(n["content"]["main"], body.lang2)
        content = {**n["content"], "translation": res["translation"], "line_checks": res["line_checks"],
                   "translation_ok": res["ok"]}
    return public_notice(store.update_notice(notice_id, n["title"], n["template"], content), True)


@app.delete("/api/notices/{notice_id}")
def delete_notice(notice_id: str, uid: str = Depends(user_id)) -> dict[str, Any]:
    store.delete_notice(notice_id, uid)
    return {"ok": True}


@app.get("/api/qr/notice/{notice_id}.svg")
def qr_notice(notice_id: str) -> Response:
    return _qr_svg(f"{PUBLIC_BASE}/notice/{notice_id}")


@app.get("/api/qr/source/{chunk_id}.svg")
def qr_source(chunk_id: str) -> Response:
    if chunk_id not in engine.chunks:
        raise HTTPException(404, "Passage not found")
    return _qr_svg(f"{PUBLIC_BASE}/chat?source={chunk_id}")


def _qr_svg(url: str) -> Response:
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", scale=4, border=1, xmldecl=False, svgns=True)
    return Response(buf.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


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
    if body.mode not in ("auto", "answer", "visual", "compare", "task_plan", "notice"):
        raise HTTPException(422, "Unknown mode")
    if not engine.ready:
        raise HTTPException(503, engine.error or "SafetyAgent is starting up.")

    def on_done(res: dict[str, Any]) -> dict[str, Any]:
        res.pop("notice_content", None)  # the test console does not store notices
        return public_message({"id": 0, "role": "assistant", "text": res["text"], "created": 0, "payload": res},
                              admin=True)

    return stream_answer(body.question.strip()[: int(web["max_question_chars"])], [], body.setup, on_done,
                         mode=body.mode)


@app.get("/api/admin/notices")
def admin_notices(status: str | None = None, _: str = Depends(admin_user)) -> dict[str, Any]:
    return {"notices": store.list_notices(status=status if status in NOTICE_STATUSES else None)}


@app.get("/api/admin/notices/{notice_id}")
def admin_notice(notice_id: str, _: str = Depends(admin_user)) -> dict[str, Any]:
    n = store.get_notice(notice_id)
    if not n:
        raise HTTPException(404, "Notice not found")
    out = public_notice(n, can_edit=False)
    out["warnings"] = _notice_warnings(n["content"])  # the reviewer sees the checks too
    return out


@app.post("/api/admin/notices/{notice_id}/approve")
def approve_notice(notice_id: str, name: str = Depends(admin_user)) -> dict[str, Any]:
    n = store.get_notice(notice_id)
    if not n:
        raise HTTPException(404, "Notice not found")
    return public_notice(store.approve_notice(notice_id, name), can_edit=False)


@app.delete("/api/admin/notices/{notice_id}")
def admin_delete_notice(notice_id: str, _: str = Depends(admin_user)) -> dict[str, Any]:
    store.delete_notice(notice_id)
    return {"ok": True}


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
