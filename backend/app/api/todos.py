from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.enums import TodoStatus
from app.db.session import get_db
from app.schemas.responses import ApiResponse
from app.schemas.todos import TodoCompletionUpdate, TodoCreate, TodoUpdate
from app.services.todos import (
    create_todo,
    get_todo,
    list_todos,
    set_todo_completion,
    update_todo,
)

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=ApiResponse)
def read_todos(
    user_id: str = Query(..., min_length=1),
    todo_date: date | None = Query(default=None, alias="date"),
    status: TodoStatus | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse:
    todos = list_todos(
        db,
        user_id=user_id,
        todo_date=todo_date,
        status=status,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data={"items": [item.model_dump(mode="json") for item in todos]})


@router.get("/{todo_id}", response_model=ApiResponse)
def read_todo(
    todo_id: str,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    todo = get_todo(db, user_id=user_id, todo_id=todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="todo not found")
    return ApiResponse(data=todo.model_dump(mode="json"))


@router.post("", response_model=ApiResponse)
def add_todo(
    payload: TodoCreate,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    todo = create_todo(db, user_id=user_id, payload=payload)
    return ApiResponse(data=todo.model_dump(mode="json"))


@router.patch("/{todo_id}", response_model=ApiResponse)
def patch_todo(
    todo_id: str,
    payload: TodoUpdate,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    todo = update_todo(db, user_id=user_id, todo_id=todo_id, payload=payload)
    if todo is None:
        raise HTTPException(status_code=404, detail="todo not found")
    return ApiResponse(data=todo.model_dump(mode="json"))


@router.patch("/{todo_id}/completion", response_model=ApiResponse)
def patch_todo_completion(
    todo_id: str,
    payload: TodoCompletionUpdate,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    todo = set_todo_completion(db, user_id=user_id, todo_id=todo_id, payload=payload)
    if todo is None:
        raise HTTPException(status_code=404, detail="todo not found")
    return ApiResponse(data=todo.model_dump(mode="json"))

