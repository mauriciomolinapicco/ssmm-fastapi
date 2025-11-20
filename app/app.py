from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.schemas import PostCreate, PostResponse
from app.db import Post, create_db_and_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import shutil
import os
import uuid 
import tempfile 
from app.users import fastapi_users, current_active_user, auth_backend



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
    if imagekit is None:
        raise HTTPException(
            status_code=500, 
            detail="ImageKit no está configurado. Por favor, configura las variables de entorno: IMAGEKIT_PUBLIC_KEY, IMAGEKIT_PRIVATE_KEY, IMAGEKIT_URL_ENDPOINT"
        )
    
    temp_file_path = None
    try:
        # we create a temporary file to store the uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file: #hacemos que la extension del archivo temp sea la misma que la del archivo original
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        upload_result = imagekit.upload_file(
            file=open(temp_file_path, "rb"),
            file_name=file.filename,
            options=UploadFileRequestOptions(
                use_unique_file_name=True,
                tags=["backend-uploaded"]
            )
        )

        if upload_result.response_metadata.http_status_code == 200:
            post = Post(
                caption=caption,
                url=upload_result.url,
                file_type="video" if file.content_type.startswith("video") else "image",
                file_name=upload_result.name,
            )

            session.add(post)
            await session.commit() #commit transaction to db
            """ hay campos como el id que se generan automaticamente y no los seteo cuando defino Post, por eso tengo que usar el refresh
            para que se actualice el objeto con el id y demas campos generados automaticamente
            """
            await session.refresh(post) 
            return post

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()
    

    


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
            "url": post.url,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat()

        })

    return {"posts":posts_data}

@app.delete("/posts/{post_id}")
async def del_post(
    post_id: str, 
    session: AsyncSession = Depends(get_async_session)
    ):

    try:
        # Validar que el post_id sea un UUID válido
        try:
            uuid.UUID(post_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid post ID format")

        # Buscar el post comparando directamente con el string (Post.id es String en la DB)
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalars().first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Eliminar el post (delete es síncrono, commit es async)
        session.delete(post)
        await session.commit()

        return {"success": True, "message": "Post deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
