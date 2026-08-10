from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Goal, GoalCompany
from app.schemas.goals import GoalRead, GoalUpsert


def get_goal(db: Session, user_id: str) -> GoalRead | None:
    goal = db.scalar(
        select(Goal)
        .where(Goal.user_id == user_id)
        .options(selectinload(Goal.companies))
    )
    if goal is None:
        return None
    return _to_read_model(goal)


def upsert_goal(db: Session, user_id: str, payload: GoalUpsert) -> GoalRead:
    goal = db.scalar(
        select(Goal)
        .where(Goal.user_id == user_id)
        .options(selectinload(Goal.companies))
    )

    if goal is None:
        goal = Goal(user_id=user_id)
        db.add(goal)

    goal.graduation_year = payload.graduation_year
    goal.target_positions = payload.target_positions
    goal.target_cities = payload.target_cities
    goal.target_industries = payload.target_industries
    goal.companies = [
        GoalCompany(company_name=item.company_name, priority=item.priority)
        for item in payload.target_companies
    ]

    db.commit()
    db.refresh(goal)
    return _to_read_model(goal)


def _to_read_model(goal: Goal) -> GoalRead:
    return GoalRead(
        id=goal.id,
        user_id=goal.user_id,
        graduation_year=goal.graduation_year,
        target_positions=goal.target_positions,
        target_cities=goal.target_cities,
        target_industries=goal.target_industries,
        target_companies=goal.companies,
    )

