"""Имя служебного проекта «корзины» для заметок из удалённых проектов."""

# Отображаемое и хранимое имя в `items.project` / registry (не использовать для новых проектов пользователем).
SYSTEM_NULL_PROJECT_NAME: str = "Null"

SYSTEM_NULL_DESCRIPTION_DEFAULT: str = (
    "Служебный проект: сюда попадают задачи из удалённых проектов с пометкой в тексте."
)


def is_reserved_system_name(name: str) -> bool:
    return name.strip() == SYSTEM_NULL_PROJECT_NAME
