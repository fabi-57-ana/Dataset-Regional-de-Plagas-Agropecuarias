# app/database.py

from supabase import create_client, Client
import cloudinary
import cloudinary.uploader
from app.config import settings

# Inicializar Cliente de Supabase
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Inicializar Configuración de Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)
