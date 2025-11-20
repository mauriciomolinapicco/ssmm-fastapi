from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.schemas import PostCreate, PostResponse, UserRead, UserCreate, UserUpdate
from app.db import Post, create_db_and_tables, get_async_session, User
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

# Rutas de autenticación JWT
app.include_router(
    fastapi_users.get_auth_router(auth_backend), 
    prefix="/auth/jwt", 
    tags=["auth"]
)

# Ruta de registro
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate), 
    prefix="/auth", 
    tags=["auth"]
)

# Ruta de reset password (forgot password + reset password)
app.include_router(
    fastapi_users.get_reset_password_router(), 
    prefix="/auth", 
    tags=["auth"]
)

# Ruta de verificación de email
app.include_router(
    fastapi_users.get_verify_router(UserRead), 
    prefix="/auth", 
    tags=["auth"]
)

# Rutas de gestión de usuarios (requiere autenticación)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate), 
    prefix="/users", 
    tags=["users"]
)

# Endpoint de diagnóstico para ver todas las rutas registradas
@app.get("/debug/routes", tags=["debug"])
async def debug_routes():
    """Endpoint de diagnóstico para ver todas las rutas registradas"""
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, "name", "N/A")
            })
    return {"total_routes": len(routes), "routes": routes}


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...), #receive file object
    caption: str = Form(""),
    user: User = Depends(current_active_user),  #PROTEGER LA RUTA solamente permitida para usuarios autenticados
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
                user_id = str(user.id),
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
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user) #proteger la ruta (solo usuarios logueados) y obtener la info del usuario
):
    res = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in res.all()]

    res = await session.execute(select(User))
    users = [row[0] for row in res.all()]
    user_dict = {u.id: u.email for u in users}

    posts_data = []
    for post in posts:
        posts_data.append({
            "id":str(post.id),
            "user_id": str(post.user_id),
            "caption": post.caption,
            "file_type": post.file_type,
            "url": post.url,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat(),
            "is_owner": str(post.user_id) == str(user.id),
            "email": user_dict.get(post.user_id, "N/A")
        })

    return {"posts":posts_data}

@app.delete("/posts/{post_id}")
async def del_post(
    post_id: str, 
    user: User = Depends(current_active_user), #proteger la ruta (solo usuarios logueados) y obtener la info del usuario
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

        if str(post.user_id) != str(user.id):
            raise HTTPException(status_code=403, detail="You are not allowed to delete this post")

        # Eliminar el post (delete es síncrono, commit es async)
        session.delete(post)
        await session.commit()

        return {"success": True, "message": "Post deleted"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
