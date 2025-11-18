from pydantic import BaseModel


#we use the class receive data from body
class PostCreate(BaseModel):
    title: str
    content: str 

class PostResponse(BaseModel):
    title: str
    content: str 

