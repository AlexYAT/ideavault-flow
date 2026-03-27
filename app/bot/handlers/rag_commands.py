"""RAG: mode switching, GitHub bind, reindex, extended stats."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.db import bot_session
from app.bot.handlers.common import telegram_user_id
from app.rag.indexer import reindex_project_scope
from app.repositories import rag_repo
from app.services import mvp_api_service, project_service

logger = logging.getLogger(__name__)


async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/mode`` | ``/mode rag`` | ``/mode vault``."""
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    args = context.args or []
    with bot_session() as db:
        if not args:
            m = project_service.get_chat_mode(db, uid)
            cur = project_service.get_current_project(db, uid)
            await update.effective_message.reply_text(
                f"Режим: {m}\nТекущий проект: {cur or '— (глобально)'}",
            )
            return
        mode = args[0].lower().strip()
        if mode not in ("rag", "vault"):
            await update.effective_message.reply_text("Использование: /mode rag  или  /mode vault")
            return
        reset = project_service.set_chat_mode(db, uid, mode)
        logger.info("user=%s chat_mode=%s", uid, mode)
    extra = "\nКонтекст чата сброшен для нового режима." if reset else ""
    await update.effective_message.reply_text(f"Режим переключён: {mode}.{extra}")


async def cmd_rag_bind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/rag_bind owner/repo [branch]`` — bind GitHub raw source to current project."""
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    if not context.args:
        await update.effective_message.reply_text(
            "Использование: /rag_bind owner/repo [ветка]\nПример: /rag_bind octocat/Hello-World main",
        )
        return
    repo_full = context.args[0].strip()
    branch = context.args[1].strip() if len(context.args) > 1 else "main"
    with bot_session() as db:
        proj = project_service.get_current_project(db, uid)
        if not proj:
            await update.effective_message.reply_text(
                "Сначала выберите проект: /set имя-проекта",
            )
            return
        rag_repo.upsert_github_binding(db, project=proj, repo_full=repo_full, branch=branch)
    await update.effective_message.reply_text(
        f"GitHub для «{proj}»: {repo_full} (ветка {branch}). "
        f"Файлы по умолчанию: README.md. Уточнить: /rag_paths README.md docs/guide.md",
    )


async def cmd_rag_paths(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/rag_paths`` — показать список; ``/rag_paths a.md b.md`` — сохранить whitelist."""
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    with bot_session() as db:
        proj = project_service.get_current_project(db, uid)
        if not proj:
            await update.effective_message.reply_text("Нужен активный проект: /set …")
            return
        args = context.args or []
        if not args:
            paths = rag_repo.list_github_paths(db, proj)
            bind = rag_repo.get_github_binding(db, proj)
            repo = bind.repo_full if bind else "—"
            await update.effective_message.reply_text(
                f"Репозиторий: {repo}\nПути:\n" + ("\n".join(f"• {p}" for p in paths) or "(пусто — используется README.md)"),
            )
            return
        row = rag_repo.set_github_paths(db, project=proj, paths=list(args))
        if row is None:
            await update.effective_message.reply_text("Сначала /rag_bind owner/repo")
            return
    await update.effective_message.reply_text("Сохранены пути:\n" + "\n".join(f"• {p}" for p in args))


async def cmd_index(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/index`` — переиндексация ``data/knowledge/`` и GitHub для текущего проекта или глобально."""
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    with bot_session() as db:
        proj = project_service.get_current_project(db, uid)
        stats = reindex_project_scope(db, project=proj)
    scope = f"«{proj}»" if proj else "глобально (_global)"
    logger.info("user=%s reindex scope=%s stats=%s", uid, proj, stats)
    await update.effective_message.reply_text(
        f"Индексация {scope}:\n"
        f"удалено документов: {stats['deleted_documents']}\n"
        f"локальных файлов: {stats['indexed_local_files']}\n"
        f"из GitHub: {stats['indexed_github_files']}",
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сводка vault + RAG (без HTTP)."""
    _ = context
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    with bot_session() as db:
        s = mvp_api_service.get_vault_stats(db)
    await update.effective_message.reply_text(
        "Статистика:\n"
        f"• Заметок (items): {s.items_total}\n"
        f"• Проектов (из items): {s.projects_total}\n"
        f"• Заметок с проектом: {s.items_with_project}\n"
        f"• Документов RAG: {s.rag_documents_total}\n"
        f"• Чанков RAG: {s.rag_chunks_total}\n"
        f"• Проектов с knowledge: {s.rag_projects_with_docs}",
    )
