# app/config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "Dataset Regional de Plagas Agropecuarias"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET")

    # Configuración JWT y Seguridad
    SECRET_KEY: str = os.getenv("SECRET_KEY", "clave_secreta_default")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

settings = Settings()