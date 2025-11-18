from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.schemas import PostCreate, PostResponse
from app.db import Post, create_db_and_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan) # cuando empezamos la app se crea la db y las tablas


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...), #receive file object
    caption: str = Form(""),
    session: AsyncSession = Depends(get_async_session) #dependency injection to get the async session (llamando a la funcion get_async_session)
):
    post = Post(
        caption=caption,
        url="abc",
        file_type="photo",
        file_name="dummy",
    )

    session.add(post)
    await session.commit() #commit transaction to db
    """ hay campos como el id que se generan automaticamente y no los seteo cuando defino Post, por eso tengo que usar el refresh
    para que se actualice el objeto con el id y demas campos generados automaticamente
    """
    await session.refresh(post) 

    return post


@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(get_async_session)
):
    res = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in res.all()]
    posts_data = []
    for post in posts:
        posts_data.append({
            "id":str(post.id),
            "caption": post.caption,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat()

        })

    return {"posts":posts_data}