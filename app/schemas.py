from pydantic import BaseModel
from fastapi_users import schemas
import uuid

#we use the class receive data from body
class PostCreate(BaseModel):
    title: str
    content: str 

class PostResponse(BaseModel):
    title: str
    content: str 

#users classes
class UserRead(schemas.BaseUser[uuid.UUID]):
    pass

class UserCreate(schemas.BaseUserCreate):
    pass

class UserUpdate(schemas.BaseUserUpdate):
    pass

# son clases que ya vienen incluidas en fastapi_users pero tenemos que crear dummy classes