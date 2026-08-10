from pydantic import BaseModel, Field

from app.db.enums import CompanyPriority


class GoalCompanyInput(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    priority: CompanyPriority


class GoalUpsert(BaseModel):
    graduation_year: str = Field(min_length=1, max_length=32)
    target_positions: list[str] = Field(min_length=1)
    target_cities: list[str] = Field(min_length=1)
    target_industries: list[str] = Field(min_length=1)
    target_companies: list[GoalCompanyInput] = Field(min_length=1, max_length=10)


class GoalCompanyRead(BaseModel):
    company_name: str
    priority: CompanyPriority

    model_config = {"from_attributes": True}


class GoalRead(BaseModel):
    id: str
    user_id: str
    graduation_year: str
    target_positions: list[str]
    target_cities: list[str]
    target_industries: list[str]
    target_companies: list[GoalCompanyRead]

