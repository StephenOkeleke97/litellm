from pydantic import BaseModel
from typing import Optional

class ConversationCreate(BaseModel):
    model_id: str
    metadata: Optional[dict] = None