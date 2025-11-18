from fastapi import FastAPI, HTTPException
from app.schemas import PostCreate, PostResponse
from app.db import Post, create_db_and_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)
# cuando empezamos la app se crea la db y las tablas


text_posts = {
    1: {"title": "Cómo optimizar consultas SQL", "content": "Guía práctica para mejorar tiempos de respuesta usando índices, EXPLAIN y particiones."},
    2: {"title": "Introducción a Docker", "content": "Conceptos básicos de contenedores, imágenes y cómo crear tu primer Dockerfile."},
    3: {"title": "Patrones de diseño en Python", "content": "Revisión de Singleton, Factory y Observer con ejemplos simples."},
    4: {"title": "Guía rápida de React Hooks", "content": "useState, useEffect y custom hooks explicados con casos reales."},
    5: {"title": "Cómo mejorar el SEO en 2025", "content": "Buenas prácticas actuales: Core Web Vitals, schema markup y contenido útil."},
    6: {"title": "Deploy de apps Django", "content": "Pasos para hacer deploy en producción con Gunicorn, Nginx y PostgreSQL."},
    7: {"title": "Versionado semántico", "content": "Explicación de MAJOR.MINOR.PATCH y cuándo aumentar cada uno."},
    8: {"title": "Qué es una API REST", "content": "Definición, principios y cómo diseñar endpoints limpios y consistentes."},
    9: {"title": "Bases de datos NoSQL vs SQL", "content": "Cuándo elegir MongoDB, Redis o PostgreSQL según el tipo de proyecto."},
    10: {"title": "Optimización de JavaScript", "content": "Técnicas modernas: lazy loading, code splitting y memoización."}
}


@app.get("/posts")
def get_posts(limit: int = None):
    if limit:
        return list(text_posts.values())[:limit]
    return text_posts


@app.get("/posts/{post_id}")
def get_post(post_id: int) -> PostResponse:
    if post_id not in text_posts:
        raise HTTPException(status_codes=404, detail="Post not found")
    return text_posts.get(post_id)


@app.post("/posts")
def create_post(post: PostCreate) -> PostResponse:  #because we use pydantic Modelo fastapi knows its in the body
    # accept data via body
    new_id = max(text_posts.keys()) + 1
    text_posts[new_id] = {"title": post.title, "content": post.content}
    return text_posts[new_id]
