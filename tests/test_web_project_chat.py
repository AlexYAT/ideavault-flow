"""Web UI project page: chat send, mode toggle, context clear."""

from urllib.parse import quote

from fastapi.testclient import TestClient


def _create_project(client: TestClient, name: str) -> None:
    r = client.post(
        "/ui/project/create",
        data={"name": name, "description": "t"},
        follow_redirects=False,
    )
    assert r.status_code == 303


def test_ui_project_page_renders_chat_block(client: TestClient) -> None:
    _create_project(client, "WebChatUi1")
    q = quote("WebChatUi1", safe="")
    r = client.get(f"/ui/project/{q}")
    assert r.status_code == 200
    assert "Чат проекта" in r.text
    assert "Отправить" in r.text
    assert "Очистить контекст" in r.text
    assert "Начните диалог" in r.text
    assert "Режим:" in r.text


def test_ui_project_chat_send_and_history(client: TestClient) -> None:
    _create_project(client, "WebChatUi2")
    q = quote("WebChatUi2", safe="")
    send = client.post(
        f"/ui/project/{q}/chat/send",
        data={"message": "  ping vault  "},
        follow_redirects=False,
    )
    assert send.status_code == 303
    page = client.get(f"/ui/project/{q}")
    assert page.status_code == 200
    assert "ping vault" in page.text


def test_ui_project_chat_clear_flash(client: TestClient) -> None:
    _create_project(client, "WebChatUi3")
    q = quote("WebChatUi3", safe="")
    client.post(f"/ui/project/{q}/chat/send", data={"message": "x"}, follow_redirects=False)
    clr = client.post(f"/ui/project/{q}/chat/clear", follow_redirects=False)
    assert clr.status_code == 303
    loc = clr.headers.get("location") or ""
    assert "/ui/project/" in loc
    page = client.get(loc)
    assert page.status_code == 200
    assert "Контекст очищен" in page.text


def test_ui_project_chat_toggle_mode_flash(client: TestClient) -> None:
    _create_project(client, "WebChatUi4")
    q = quote("WebChatUi4", safe="")
    t = client.post(f"/ui/project/{q}/chat/toggle-mode", follow_redirects=False)
    assert t.status_code == 303
    page = client.get(t.headers.get("location") or "")
    assert page.status_code == 200
    assert "Режим: RAG" in page.text


def test_ui_project_chat_empty_message_rejected(client: TestClient) -> None:
    _create_project(client, "WebChatUi5")
    q = quote("WebChatUi5", safe="")
    r = client.post(f"/ui/project/{q}/chat/send", data={"message": "  "}, follow_redirects=False)
    assert r.status_code == 303
    assert "msg=" in (r.headers.get("location") or "")


def test_list_active_thread_messages_empty_after_fresh_thread(db_session) -> None:
    """Новый thread после clear — на экране пустая история, старые сообщения в БД остаются."""
    from app.repositories import project_registry_repo
    from app.services import chat_history_service, project_service
    from app.services.bot_dialog_service import process_incoming_text

    project_registry_repo.create(db_session, name="FreshChatP", description="")
    uid = "fresh-chat-user"
    project_service.set_current_project(db_session, uid, "FreshChatP")
    process_incoming_text(db_session, uid, "hello line")
    assert len(chat_history_service.list_active_thread_messages(db_session, uid)) >= 2
    chat_history_service.start_fresh_thread(db_session, uid)
    assert chat_history_service.list_active_thread_messages(db_session, uid) == []
