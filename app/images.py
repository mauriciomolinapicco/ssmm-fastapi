from dotenv import load_dotenv
from imagekitio import ImageKit
import os
from pathlib import Path

# Buscar el archivo .env en la raíz del proyecto
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Inicializar ImageKit solo si las variables de entorno están configuradas
public_key = os.getenv("IMAGEKIT_PUBLIC_KEY")
private_key = os.getenv("IMAGEKIT_PRIVATE_KEY")
url_endpoint = os.getenv("IMAGEKIT_URL")

if not env_path.exists():
    print(f"⚠️  Advertencia: No se encontró el archivo .env en {env_path}")
else:
    print(f"✅ Archivo .env encontrado en {env_path}")
    if not (public_key and private_key and url_endpoint):
        print("⚠️  Advertencia: Faltan variables de entorno de ImageKit en el archivo .env")

if public_key and private_key and url_endpoint:
    imagekit = ImageKit(
        public_key=public_key,
        private_key=private_key,
        url_endpoint=url_endpoint,
    )
else:
    imagekit = None
 