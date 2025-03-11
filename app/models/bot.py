from pydantic import BaseModel, validator
from typing import Optional, List

class NodeCreate(BaseModel):
    id: str
    text: str
    next: Optional[str] = None
    options: Optional[List[str]] = None

    @validator('options', pre=True)
    def validate_options(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            v = [opt.strip() for opt in v.split(',') if opt.strip()]
        if not v:
            return []
        return v

class BotCreate(BaseModel):
    name: str
    token: str
