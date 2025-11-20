from collections.abc import AsyncGenerator
import uuid 
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from fastapi import Depends


DATABASE_URL = "sqlite+aiosqlite:///./test.db" #async version of sqlite

class Base(DeclarativeBase): # esto es porque no podemos heredar directamente de DeclarativeBase
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    #creamos para tener una relacion entre usuario y posts
    __tablename__ = "users"
    posts = relationship("Post", back_populates="user") 

class Post(Base):
    __tablename__ = "posts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
     #creamos una relacion one to many: 1 user -> n posts
     # si quisieramos invertir la relacion definiriamos la FK en User
    caption = Column(Text)
    url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="posts")
   

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        #find the clases that inherit from DeclarativeBase and create the tables

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
        #gets a session that access the db 


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)