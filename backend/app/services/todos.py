from datetime import date, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.enums import TodoStatus
from app.db.models import Todo
from app.schemas.todos import TodoCompletionUpdate, TodoCreate, TodoRead, TodoUpdate


def list_todos(
    db: Session,
    *,
    user_id: str,
    todo_date: date | None = None,
    status: TodoStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TodoRead]:
    statement: Select[tuple[Todo]] = (
        select(Todo)
        .where(Todo.user_id == user_id)
        .order_by(Todo.date.desc(), Todo.priority_order.asc().nullslast(), Todo.created_at.desc())
    )

    if todo_date is not None:
        statement = statement.where(Todo.date == todo_date)
    if status is not None:
        statement = statement.where(Todo.status == status)

    todos = db.scalars(statement.limit(limit).offset(offset)).all()
    return [TodoRead.model_validate(todo) for todo in todos]


def get_todo(db: Session, *, user_id: str, todo_id: str) -> TodoRead | None:
    todo = _get_todo(db, user_id=user_id, todo_id=todo_id)
    if todo is None:
        return None
    return TodoRead.model_validate(todo)


def create_todo(db: Session, *, user_id: str, payload: TodoCreate) -> TodoRead:
    todo = Todo(user_id=user_id, status=TodoStatus.pending, **payload.model_dump())
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return TodoRead.model_validate(todo)


def update_todo(
    db: Session,
    *,
    user_id: str,
    todo_id: str,
    payload: TodoUpdate,
) -> TodoRead | None:
    todo = _get_todo(db, user_id=user_id, todo_id=todo_id)
    if todo is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(todo, field, value)

    if "status" in update_data and todo.status != TodoStatus.completed:
        todo.completed_at = None
        todo.completion_source = None

    db.commit()
    db.refresh(todo)
    return TodoRead.model_validate(todo)


def set_todo_completion(
    db: Session,
    *,
    user_id: str,
    todo_id: str,
    payload: TodoCompletionUpdate,
) -> TodoRead | None:
    todo = _get_todo(db, user_id=user_id, todo_id=todo_id)
    if todo is None:
        return None

    if payload.completed:
        todo.status = TodoStatus.completed
        todo.completed_at = datetime.utcnow()
        todo.completion_source = payload.completion_source
    else:
        todo.status = TodoStatus.pending
        todo.completed_at = None
        todo.completion_source = None

    db.commit()
    db.refresh(todo)
    return TodoRead.model_validate(todo)


def _get_todo(db: Session, *, user_id: str, todo_id: str) -> Todo | None:
    return db.scalar(
        select(Todo)
        .where(Todo.id == todo_id)
        .where(Todo.user_id == user_id)
    )

