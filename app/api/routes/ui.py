"""Minimal Jinja2 HTML UI for projects, RAG binding, moving items."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.enums import CaptureSource
from app.core.project_constants import SYSTEM_NULL_PROJECT_NAME
from app.db.base import get_db
from app.rag.indexer import reindex_project_scope
from app.repositories import items_repo, project_registry_repo, rag_repo
from app.services import bot_dialog_service, chat_history_service, project_dashboard_service, project_service
from app.services.rag_binding_service import format_bind_result_message, validate_github_paths
from app.services.telegram_photo_service import PROJECT_ROOT

router = APIRouter(prefix="/ui", tags=["ui"])

_TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES))

DATA_ROOT = (PROJECT_ROOT / "data").resolve()

_IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})


def resolve_path_under_data(rel_path: str) -> Path | None:
    """Путь только внутри ``data/``; иначе ``None``."""
    stripped = (rel_path or "").strip()
    if not stripped:
        return None
    p = Path(stripped.replace("\\", "/"))
    candidate = p.resolve() if p.is_absolute() else (PROJECT_ROOT / p).resolve()
    try:
        candidate.relative_to(DATA_ROOT)
    except ValueError:
        return None
    return candidate


def attachment_is_image_preview(source: str, ref: str) -> bool:
    if source == CaptureSource.TELEGRAM_PHOTO.value:
        return True
    suf = Path(ref.replace("\\", "/")).suffix.lower()
    return suf in _IMAGE_SUFFIXES


def _redirect(url: str, msg: str) -> RedirectResponse:
    q = quote(msg, safe="")
    return RedirectResponse(f"{url}?msg={q}", status_code=303)


def _redirect_rag(project: str, msg: str) -> RedirectResponse:
    p = quote(project.strip(), safe="")
    m = quote(msg, safe="")
    return RedirectResponse(f"/ui/rag?project={p}&msg={m}", status_code=303)


def _redirect_items_list(msg: str, *, list_project: str | None = None) -> RedirectResponse:
    """Редирект на список задач; сохраняет фильтр ``project=``, если он был на странице."""
    qmsg = quote(msg, safe="")
    scope = (list_project or "").strip()
    if scope:
        pq = quote(scope, safe="")
        return RedirectResponse(f"/ui/items?project={pq}&msg={qmsg}", status_code=303)
    return RedirectResponse(f"/ui/items?msg={qmsg}", status_code=303)


@router.get("/files")
def ui_serve_data_file(
    path: str = Query(..., min_length=1, description="raw_payload_ref внутри data/"),
) -> FileResponse:
    """Отдаёт файл из ``data/``; произвольные пути снаружи запрещены."""
    resolved = resolve_path_under_data(path)
    if resolved is None:
        raise HTTPException(status_code=403, detail="Path not allowed")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=resolved, filename=resolved.name)


# --- Dashboard & project CRUD (product UI) ---


@router.get("")
def ui_dashboard(request: Request, db: Session = Depends(get_db)) -> object:
    rows = project_dashboard_service.list_dashboard_rows(db)
    msg = request.query_params.get("msg")
    return templates.TemplateResponse(
        request,
        "ui_dashboard.html",
        {"rows": rows, "msg": msg},
    )


@router.get("/project/new")
def ui_project_new_form(request: Request) -> object:
    msg = request.query_params.get("msg")
    return templates.TemplateResponse(request, "ui_project_new.html", {"msg": msg})


@router.post("/project/create")
def ui_project_create(
    name: str = Form(...),
    description: str = Form(default=""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        project_dashboard_service.create_project(db, name=name, description=description)
    except ValueError as exc:
        return _redirect("/ui/project/new", str(exc))
    return _redirect("/ui", f"Проект «{name.strip()}» создан")


@router.get("/project/{name}/delete-confirm")
def ui_project_delete_confirm(
    request: Request,
    name: str,
    db: Session = Depends(get_db),
) -> object:
    if name == SYSTEM_NULL_PROJECT_NAME:
        return _redirect("/ui", "Служебный проект Null нельзя удалить")
    names = set(project_registry_repo.list_union_names(db))
    if name not in names:
        return _redirect("/ui", "Проект не найден")
    nu = quote(name, safe="")
    return templates.TemplateResponse(
        request,
        "ui_project_delete.html",
        {"name": name, "name_url": nu, "msg": request.query_params.get("msg")},
    )


@router.post("/project/{name}/delete")
def ui_project_delete_execute(name: str, db: Session = Depends(get_db)) -> RedirectResponse:
    try:
        project_dashboard_service.delete_project_cascade(db, name=name)
    except ValueError as exc:
        return _redirect("/ui", str(exc))
    return _redirect("/ui", f"Проект «{name}» удалён; задачи перенесены в {SYSTEM_NULL_PROJECT_NAME}")


@router.get("/project/{name}/edit")
def ui_project_edit_form(
    request: Request,
    name: str,
    db: Session = Depends(get_db),
) -> object:
    if name not in project_registry_repo.list_union_names(db):
        return _redirect("/ui", "Проект не найден")
    reg = project_registry_repo.get(db, name)
    desc = reg.description if reg else ""
    nu = quote(name, safe="")
    return templates.TemplateResponse(
        request,
        "ui_project_edit.html",
        {
            "name": name,
            "name_url": nu,
            "description": desc,
            "msg": request.query_params.get("msg"),
        },
    )


@router.post("/project/{name}/edit")
def ui_project_edit_save(
    name: str,
    description: str = Form(default=""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if name not in project_registry_repo.list_union_names(db):
        return _redirect("/ui", "Проект не найден")
    project_dashboard_service.update_project(db, name=name, description=description)
    nu = quote(name, safe="")
    return _redirect(f"/ui/project/{nu}", "Описание обновлено")


def _ui_web_user_id() -> str:
    return get_settings().web_ui_user_id


@router.post("/project/{name}/chat/send")
def ui_project_chat_send(
    name: str,
    db: Session = Depends(get_db),
    message: str = Form(default=""),
) -> RedirectResponse:
    names = set(project_registry_repo.list_union_names(db))
    if name not in names:
        return _redirect("/ui", "Проект не найден")
    text = (message or "").strip()
    nu = quote(name, safe="")
    if not text:
        return _redirect(f"/ui/project/{nu}", "Введите сообщение")
    uid = _ui_web_user_id()
    project_service.set_current_project(db, uid, name)
    bot_dialog_service.process_incoming_text(db, uid, text)
    return RedirectResponse(f"/ui/project/{nu}", status_code=303)


@router.post("/project/{name}/chat/clear")
def ui_project_chat_clear(name: str, db: Session = Depends(get_db)) -> RedirectResponse:
    names = set(project_registry_repo.list_union_names(db))
    if name not in names:
        return _redirect("/ui", "Проект не найден")
    uid = _ui_web_user_id()
    project_service.set_current_project(db, uid, name)
    chat_history_service.start_fresh_thread(db, uid)
    nu = quote(name, safe="")
    return _redirect(f"/ui/project/{nu}", "Контекст очищен")


@router.post("/project/{name}/chat/toggle-mode")
def ui_project_chat_toggle_mode(name: str, db: Session = Depends(get_db)) -> RedirectResponse:
    names = set(project_registry_repo.list_union_names(db))
    if name not in names:
        return _redirect("/ui", "Проект не найден")
    uid = _ui_web_user_id()
    project_service.set_current_project(db, uid, name)
    cur = project_service.get_chat_mode(db, uid)
    nxt = "rag" if cur == "vault" else "vault"
    project_service.set_chat_mode(db, uid, nxt)
    label = "Режим: RAG" if nxt == "rag" else "Режим: без RAG (заметки)"
    nu = quote(name, safe="")
    return _redirect(f"/ui/project/{nu}", label)


@router.post("/project/{name}/rag/reindex")
def ui_project_rag_reindex(name: str, db: Session = Depends(get_db)) -> RedirectResponse:
    """Тот же контур, что ``POST /rag/index``: :func:`~app.rag.indexer.reindex_project_scope`."""
    names = set(project_registry_repo.list_union_names(db))
    if name not in names:
        return _redirect("/ui", "Проект не найден")
    nu = quote(name, safe="")
    try:
        stats = reindex_project_scope(db, project=name)
    except Exception as exc:
        return _redirect(f"/ui/project/{nu}", f"Ошибка переиндексации RAG: {exc}")
    msg = (
        "RAG переиндексирован: удалено документов {del_}, локальных файлов {loc_}, GitHub {gh_}."
    ).format(
        del_=stats["deleted_documents"],
        loc_=stats["indexed_local_files"],
        gh_=stats["indexed_github_files"],
    )
    return _redirect(f"/ui/project/{nu}", msg)


@router.get("/project/{name}")
def ui_project_open(request: Request, name: str, db: Session = Depends(get_db)) -> object:
    if name not in project_registry_repo.list_union_names(db):
        return _redirect("/ui", "Проект не найден")
    uid = _ui_web_user_id()
    project_service.set_current_project(db, uid, name)
    chat_mode = project_service.get_chat_mode(db, uid)
    chat_messages_raw = chat_history_service.list_active_thread_messages(db, uid, limit=200)
    chat_messages = [{"role": m.role, "content": m.content} for m in chat_messages_raw]
    chat_empty = len(chat_messages) == 0
    reg = project_registry_repo.get(db, name)
    desc = reg.description if reg else ""
    is_sys = bool(reg and reg.is_system)
    nu = quote(name, safe="")
    local_files = project_dashboard_service.list_local_rag_files(name)
    bind = rag_repo.get_github_binding(db, name)
    github_binding: dict[str, object] | None = None
    if bind is not None:
        github_binding = {
            "repo": bind.repo_full,
            "branch": bind.branch,
            "files": rag_repo.list_github_paths(db, name),
        }
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "ui_project_detail.html",
        {
            "name": name,
            "name_url": nu,
            "description": desc,
            "is_system": is_sys,
            "local_files": local_files,
            "github_binding": github_binding,
            "chat_mode": chat_mode,
            "chat_messages": chat_messages,
            "chat_empty": chat_empty,
            "llm_enabled": bool(settings.llm_enabled),
            "msg": request.query_params.get("msg"),
        },
    )


@router.post("/projects/set")
def ui_projects_set(
    project: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    reset = project_service.set_current_project(db, settings.web_ui_user_id, project.strip())
    hint = "Текущий проект обновлён" + (" (контекст чата сброшен)." if reset else ".")
    return _redirect("/ui", hint)


@router.get("/rag")
def ui_rag_page(
    request: Request,
    db: Session = Depends(get_db),
    project: str | None = Query(None, description="Проект, для которого показывается binding"),
) -> object:
    settings = get_settings()
    uid = settings.web_ui_user_id
    current = project_service.get_current_project(db, uid)
    projects = project_service.list_all_ui_projects(db)
    qp = (project or "").strip()
    nav_from_query_project: str | None = None
    nav_from_query_url: str | None = None
    rag_scoped = False
    if qp and qp in projects:
        selected: str | None = qp
        nav_from_query_project = qp
        nav_from_query_url = quote(qp, safe="")
        project_service.set_current_project(db, uid, qp)
        rag_scoped = True
    elif current and current in projects:
        selected = current
    else:
        selected = projects[0] if projects else None
    binding = rag_repo.get_github_binding(db, selected) if selected else None
    pref_repo = binding.repo_full if binding else ""
    pref_branch = binding.branch if binding else "main"
    paths = rag_repo.list_github_paths(db, selected) if selected else []
    pref_files = "\n".join(paths)
    msg = request.query_params.get("msg")
    return templates.TemplateResponse(
        request,
        "ui_rag.html",
        {
            "projects": projects,
            "selected_project": selected or "",
            "nav_from_query_project": nav_from_query_project,
            "nav_from_query_url": nav_from_query_url,
            "rag_scoped": rag_scoped,
            "pref_repo": pref_repo,
            "pref_branch": pref_branch,
            "pref_files": pref_files,
            "msg": msg,
        },
    )


@router.post("/rag/bind")
def ui_rag_bind(
    project: str = Form(...),
    repo: str = Form(...),
    branch: str = Form(default="main"),
    files: str = Form(default=""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    pname = project.strip()
    if not pname:
        return _redirect("/ui/rag", "Укажите проект")
    repo_full = repo.strip()
    branch_clean = (branch or "main").strip() or "main"
    lines = [ln.strip() for ln in (files or "").splitlines() if ln.strip()]
    if not lines:
        return _redirect_rag(pname, "Укажите хотя бы один путь к файлу (по строке).")
    result = validate_github_paths(repo_full, branch_clean, lines)
    if result is None:
        return _redirect_rag(pname, "Укажите хотя бы один путь к файлу (по строке).")
    if result.all_invalid:
        return _redirect_rag(pname, format_bind_result_message(pname, result))
    rag_repo.upsert_github_binding(
        db,
        project=pname,
        repo_full=repo_full,
        branch=branch_clean,
        paths=result.valid,
    )
    return _redirect_rag(pname, format_bind_result_message(pname, result))


@router.get("/items")
def ui_items_page(
    request: Request,
    db: Session = Depends(get_db),
    project: str | None = Query(None, description="Фильтр по проекту"),
) -> object:
    filt: str | None = (project.strip() if project and project.strip() else None)
    filter_project_url = quote(filt, safe="") if filt else None
    rows = items_repo.list_items(db, project=filt, limit=200)
    project_options = [
        p for p in project_service.list_all_ui_projects(db) if p != SYSTEM_NULL_PROJECT_NAME
    ]
    msg = request.query_params.get("msg")
    return templates.TemplateResponse(
        request,
        "ui_items.html",
        {
            "items": rows,
            "project_options": project_options,
            "filter_project": filt,
            "filter_project_url": filter_project_url,
            "filter_project_for_query": quote(filt, safe="") if filt else None,
            "system_null_name": SYSTEM_NULL_PROJECT_NAME,
            "msg": msg,
        },
    )


@router.get("/items/{item_id}/edit")
def ui_item_edit_form(
    request: Request,
    item_id: int,
    db: Session = Depends(get_db),
    return_project: str | None = Query(None, description="Фильтр списка после сохранения"),
) -> object:
    row = items_repo.get_item(db, item_id)
    if row is None:
        return _redirect("/ui/items", "Заметка не найдена")
    rp = (return_project or "").strip() or None
    qproj = quote(rp, safe="") if rp else ""
    ref = (row.raw_payload_ref or "").strip() or None
    file_open_url: str | None = None
    file_missing = False
    show_image_preview = False
    if ref:
        resolved = resolve_path_under_data(ref)
        if resolved is None or not resolved.is_file():
            file_missing = True
        else:
            file_open_url = f"/ui/files?path={quote(ref, safe='')}"
            show_image_preview = attachment_is_image_preview(row.source, ref)
    return templates.TemplateResponse(
        request,
        "ui_item_edit.html",
        {
            "item": row,
            "return_project": rp,
            "return_project_q": qproj,
            "msg": request.query_params.get("msg"),
            "file_open_url": file_open_url,
            "file_missing": bool(ref and file_missing),
            "show_image_preview": show_image_preview,
        },
    )


@router.post("/items/{item_id}/edit")
def ui_item_edit_save(
    item_id: int,
    db: Session = Depends(get_db),
    text: str = Form(default=""),
    return_project: str = Form(default=""),
) -> RedirectResponse:
    list_scope = (return_project or "").strip() or None
    row = items_repo.update_item_text(db, item_id, text)
    if row is None:
        return _redirect_items_list("Заметка не найдена", list_project=list_scope)
    return _redirect_items_list("Заметка обновлена", list_project=list_scope)


@router.post("/items/move")
def ui_items_move(
    item_id: int = Form(...),
    project: str = Form(default=""),
    return_project: str = Form(default=""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    new_project = project.strip() or None
    list_scope = (return_project or "").strip() or None
    row = items_repo.set_item_project(db, item_id, new_project)
    if row is None:
        return _redirect_items_list(
            f"Заметка id={item_id} не найдена",
            list_project=list_scope,
        )
    label = new_project or "глобально"
    return _redirect_items_list(
        f"Заметка #{item_id} → «{label}»",
        list_project=list_scope,
    )
