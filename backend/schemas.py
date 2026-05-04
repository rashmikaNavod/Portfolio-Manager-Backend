from pydantic import BaseModel
from typing import Optional


#Project schema
class ProjectBase(BaseModel):
    title: str
    description: str
    tech_stack: Optional[str] = None
    github_link: Optional[str] = None
    image_url: Optional[str] = None   

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int

    class Config:
        from_attributes = True


#User schema
class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True