# main.py

import csv
import io
import zipfile
from io import StringIO
from typing import List, Optional
import csv
from fastapi.staticfiles import StaticFiles
import os

import cloudinary.uploader
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from PIL import Image
from pydantic import BaseModel

from app.config import settings
from app.database import supabase
# Importamos get_current_user (o el alias que utilices en dependencies)
from app.dependencies import get_current_user, require_roles
from app.schemas import (
    CambiarRolIn,
    DatasetPaginadoOut,
    EstadoValidacion,
    HallazgoOut,
    LoginIn,
    RechazoSchema,
    RolUsuario,
    TipoProduccion,
    TokenOut,
    UsuarioCreate,
    UsuarioOut,
    ValidacionExpertoIn,
)
from app.security import create_access_token, hash_password, verify_password

app = FastAPI(
    title=f"{settings.APP_NAME} - Agro API",
    description="API para la captura, etiquetado y validación de plagas agrícolas locales.",
    version="1.0.0",
    debug=settings.DEBUG,
)

# Permitir peticiones desde cualquier origen (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, PUT, DELETE, OPTIONS, etc.
    allow_headers=["*"],  # Permite encabezados como Authorization
)

# Permite servir los archivos estáticos desde la carpeta frontend
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Resolución mínima aceptable
ANCHO_MINIMO = 1280
ALTO_MINIMO = 720


@app.get("/", response_class=FileResponse)
def read_root():
    # Devuelve el index.html alojado dentro de la carpeta frontend
    return FileResponse("frontend/index.html")


# ==========================================
# MÓDULO DE AUTENTICACIÓN Y USUARIOS
# ==========================================


@app.post(
    "/api/auth/registro",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
)
def registrar_usuario(usuario: UsuarioCreate):
    # Verificar si el email ya existe
    existe = (
        supabase.table("usuarios")
        .select("email")
        .eq("email", usuario.email)
        .execute()
    )
    if existe.data:
        raise HTTPException(
            status_code=400, detail="El email ya se encuentra registrado."
        )

    password_cifrada = hash_password(usuario.password)

    nuevo_usuario = {
        "nombre": usuario.nombre,
        "email": usuario.email,
        "password_hash": password_cifrada,
        "rol": "PRODUCTOR",
    }

    response = supabase.table("usuarios").insert(nuevo_usuario).execute()
    if not response.data:
        raise HTTPException(
            status_code=500, detail="Error al registrar el usuario."
        )

    return response.data[0]


@app.post("/api/auth/login", response_model=TokenOut)
def login(credenciales: LoginIn):
    response = (
        supabase.table("usuarios")
        .select("*")
        .eq("email", credenciales.email)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=400,
            detail="Credenciales incorrectas (email no encontrado).",
        )

    usuario = response.data[0]
    if not verify_password(credenciales.password, usuario["password_hash"]):
        raise HTTPException(
            status_code=400,
            detail="Credenciales incorrectas (contraseña inválida).",
        )

    access_token = create_access_token(
        data={"sub": usuario["email"], "rol": usuario["rol"]}
    )
    usuario_out = UsuarioOut(
        id=usuario["id"],
        nombre=usuario["nombre"],
        email=usuario["email"],
        rol=usuario["rol"],
        created_at=usuario["created_at"],
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": usuario_out,
    }


@app.get("/api/auth/me")
def obtener_perfil_usuario(usuario_actual: dict = Depends(get_current_user)):
    try:
        return {
            "id": usuario_actual.get("id"),
            "nombre": usuario_actual.get("nombre"),
            "email": usuario_actual.get("email"),
            "rol": usuario_actual.get("rol"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el perfil de usuario: {str(e)}",
        )


@app.put("/api/usuarios/{usuario_id}/cambiar-rol", response_model=UsuarioOut)
def cambiar_rol_usuario(
    usuario_id: str,
    datos_rol: CambiarRolIn,
    usuario_actual: dict = Depends(require_roles([RolUsuario.ADMIN])),
):
    try:
        actualizacion = {"rol": datos_rol.nuevo_rol.value}
        response = (
            supabase.table("usuarios")
            .update(actualizacion)
            .eq("id", usuario_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=404, detail="No se encontró el usuario especificado."
            )
        return response.data[0]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al cambiar el rol: {str(e)}"
        )


# ==========================================
# MÓDULO DE HALLAZGOS Y PLAGAS
# ==========================================


@app.post("/api/hallazgos/subir", status_code=status.HTTP_201_CREATED)
async def subir_hallazgo(
    file: UploadFile = File(...),
    tipo_agro: str = Form(...),
    cultivo: str = Form(...),
    parte_afectada: str = Form(None),
    ubicacion_lat: float = Form(None),
    ubicacion_lon: float = Form(None),
    observacion_usuario: str = Form(None),
    usuario_actual: dict = Depends(get_current_user),
):
    # 1. Validar tipo de archivo
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo subido no es una imagen válida.",
        )

    # 2. Leer imagen en memoria
    contenido_bytes = await file.read()
    try:
        imagen = Image.open(io.BytesIO(contenido_bytes))
        ancho, alto = imagen.size
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al procesar la estructura de la imagen.",
        )

    # 3. Validación de Resolución
    es_horizontal_valido = ancho >= ANCHO_MINIMO and alto >= ALTO_MINIMO
    es_vertical_valido = alto >= ANCHO_MINIMO and ancho >= ALTO_MINIMO

    if not (es_horizontal_valido or es_vertical_valido):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resolución insuficiente ({ancho}x{alto}px). La imagen debe tener al menos {ANCHO_MINIMO}x{ALTO_MINIMO} píxeles.",
        )

    # 4. Subir a Cloudinary
    try:
        resultado_cloudinary = cloudinary.uploader.upload(
            contenido_bytes, folder="plagas_cordoba"
        )
        url_imagen = resultado_cloudinary.get("secure_url")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir imagen a Cloudinary: {str(e)}",
        )

    # 5. Guardar en Supabase
    datos_muestra = {
        "tipo_agro": tipo_agro,
        "cultivo": cultivo,
        "parte_afectada": parte_afectada,
        "ubicacion_lat": ubicacion_lat,
        "ubicacion_lon": ubicacion_lon,
        "observacion_usuario": observacion_usuario,
        "imagen_url": url_imagen,
        "estado": "PENDIENTE",
        "usuario_id": usuario_actual["id"],
    }

    supabase.table("hallazgos").insert(datos_muestra).execute()

    return {
        "mensaje": "Muestra subida con éxito y validada en resolución",
        "dimensiones": f"{ancho}x{alto}px",
        "imagen_url": url_imagen,
    }


@app.post("/api/hallazgos/subir-masivo", status_code=status.HTTP_201_CREATED)
async def subir_hallazgo_masivo(
    archivo_zip: UploadFile = File(...),  # <-- Cambiado 'file' a 'archivo_zip'
    tipo_agro: str = Form(...),
    cultivo: str = Form(...),
    observacion_usuario: str = Form(None),
    usuario_actual: dict = Depends(get_current_user),
):
    # En el resto de la función reemplaza 'file' por 'archivo_zip'
    if not (
        archivo_zip.filename.endswith(".zip")
        or archivo_zip.content_type in ["application/zip", "application/x-zip-compressed"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un paquete en formato .ZIP",
        )

    contenido_zip = await archivo_zip.read()
    imagenes_procesadas = []
    imagenes_descartadas = []

    try:
        with zipfile.ZipFile(io.BytesIO(contenido_zip)) as zip_ref:
            for nombre_archivo in zip_ref.namelist():
                if (
                    nombre_archivo.startswith("__MACOSX")
                    or nombre_archivo.endswith("/")
                    or nombre_archivo.startswith(".")
                ):
                    continue

                if not nombre_archivo.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".webp")
                ):
                    continue

                bytes_imagen = zip_ref.read(nombre_archivo)
                try:
                    imagen = Image.open(io.BytesIO(bytes_imagen))
                    ancho, alto = imagen.size
                    es_horizontal_valido = (
                        ancho >= ANCHO_MINIMO and alto >= ALTO_MINIMO
                    )
                    es_vertical_valido = (
                        alto >= ANCHO_MINIMO and ancho >= ALTO_MINIMO
                    )

                    if not (es_horizontal_valido or es_vertical_valido):
                        imagenes_descartadas.append(
                            {
                                "archivo": nombre_archivo,
                                "motivo": f"Resolución insuficiente ({ancho}x{alto}px). Requerido: {ANCHO_MINIMO}x{ALTO_MINIMO}px",
                            }
                        )
                        continue

                    res_cloud = cloudinary.uploader.upload(
                        bytes_imagen, folder="plagas_cordoba"
                    )
                    url_img = res_cloud.get("secure_url")

                    datos_muestra = {
                        "tipo_agro": tipo_agro,
                        "cultivo": cultivo,
                        "observacion_usuario": f"{observacion_usuario or ''} (Carga Masiva: {nombre_archivo})".strip(),
                        "imagen_url": url_img,
                        "estado": "PENDIENTE",
                        "origen_carga": "MASIVO",
                        "usuario_id": usuario_actual["id"],
                    }

                    supabase.table("hallazgos").insert(datos_muestra).execute()

                    imagenes_procesadas.append(
                        {
                            "archivo": nombre_archivo,
                            "url": url_img,
                            "dimensiones": f"{ancho}x{alto}px",
                        }
                    )
                except Exception as e:
                    imagenes_descartadas.append(
                        {
                            "archivo": nombre_archivo,
                            "motivo": f"Error al procesar la imagen: {str(e)}",
                        }
                    )
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo ZIP está dañado o es inválido.",
        )

    return {
        "mensaje": f"Proceso finalizado. {len(imagenes_procesadas)} imágenes aceptadas, {len(imagenes_descartadas)} descartadas.",
        "imagenes_aceptadas": imagenes_procesadas,
        "imagenes_descartadas": imagenes_descartadas,
    }


@app.get("/api/hallazgos/", response_model=List[HallazgoOut])
def listar_hallazgos():
    try:
        response = (
            supabase.table("hallazgos")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar la base de datos: {str(e)}",
        )


@app.get("/api/hallazgos/pendientes", response_model=List[HallazgoOut])
def listar_pendientes(
    usuario_actual: dict = Depends(
        require_roles([RolUsuario.AGRONOMO, RolUsuario.ADMIN])
    ),
):
    try:
        response = (
            supabase.table("hallazgos")
            .select("*")
            .eq("estado", "PENDIENTE")
            .order("created_at", desc=True)
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al consultar pendientes: {str(e)}"
        )


@app.put("/api/hallazgos/{hallazgo_id}/validar", response_model=HallazgoOut)
def validar_hallazgo(
    hallazgo_id: str,
    datos_validacion: ValidacionExpertoIn,
    usuario_actual: dict = Depends(
        require_roles([RolUsuario.AGRONOMO, RolUsuario.ADMIN])
    ),
):
    if datos_validacion.estado == EstadoValidacion.PENDIENTE:
        raise HTTPException(
            status_code=400,
            detail="El nuevo estado debe ser 'VALIDADO' o 'RECHAZADO'.",
        )
    try:
        actualizacion = {
            "estado": datos_validacion.estado.value,
            "etiqueta_experto": datos_validacion.etiqueta_experto,
            "observacion_experto": datos_validacion.observacion_experto,
            "experto_id": usuario_actual.get("id"),
        }
        response = (
            supabase.table("hallazgos")
            .update(actualizacion)
            .eq("id", hallazgo_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró el hallazgo con ID: {hallazgo_id}",
            )
        return response.data[0]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al validar el hallazgo: {str(e)}"
        )


@app.put("/api/hallazgos/{id}/rechazar")
def rechazar_hallazgo(
    id: str,
    datos: RechazoSchema,
    usuario_actual: dict = Depends(
        require_roles([RolUsuario.AGRONOMO, RolUsuario.ADMIN])
    ),
):
    if not datos.motivo_rechazo.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes especificar un motivo válido para rechazar la muestra.",
        )
    try:
        respuesta = (
            supabase.table("hallazgos")
            .update(
                {
                    "estado": "RECHAZADO",
                    "observacion_experto": datos.motivo_rechazo,
                    "experto_id": usuario_actual.get("id"),
                }
            )
            .eq("id", id)
            .execute()
        )
        if not respuesta.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró ninguna muestra con el ID: {id}",
            )
        return {
            "mensaje": "Muestra rechazada correctamente",
            "hallazgo_id": id,
            "motivo": datos.motivo_rechazo,
        }
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al procesar el rechazo de la muestra: {str(e)}",
        )


# ==========================================
# MÓDULO DE DATASET Y EXPORTACIÓN
# ==========================================


@app.get("/api/dataset/validado", response_model=DatasetPaginadoOut)
def obtener_dataset_validado(
    tipo_agro: Optional[TipoProduccion] = None,
    cultivo: Optional[str] = None,
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(
        20, ge=1, le=100, description="Cantidad de registros por página"
    ),
):
    try:
        offset = (page - 1) * limit
        query = (
            supabase.table("hallazgos")
            .select("*", count="exact")
            .eq("estado", "VALIDADO")
        )

        if tipo_agro:
            query = query.eq("tipo_agro", tipo_agro.value)
        if cultivo:
            query = query.ilike("cultivo", f"%{cultivo}%")

        response = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        total_registros = (
            response.count
            if response.count is not None
            else len(response.data)
        )
        total_paginas = (
            (total_registros + limit - 1) // limit if total_registros > 0 else 1
        )

        return {
            "pagina_actual": page,
            "limite_por_pagina": limit,
            "total_registros": total_registros,
            "total_paginas": total_paginas,
            "datos": response.data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar el dataset validado: {str(e)}",
        )


@app.get("/api/dataset/exportar/csv")
def exportar_dataset_csv():
    try:
        response = (
            supabase.table("hallazgos")
            .select("*")
            .eq("estado", "VALIDADO")
            .order("created_at", desc=True)
            .execute()
        )
        datos = response.data
        if not datos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay registros validados disponibles para exportar.",
            )

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "ID",
                "Tipo Agro",
                "Cultivo",
                "Parte Afectada",
                "Diagnostico Experto",
                "Observacion Experto",
                "Latitud",
                "Longitud",
                "URL Imagen",
                "Fecha Carga",
            ]
        )

        for row in datos:
            writer.writerow(
                [
                    row.get("id"),
                    row.get("tipo_agro"),
                    row.get("cultivo"),
                    row.get("parte_afectada", ""),
                    row.get("etiqueta_experto", ""),
                    row.get("observacion_experto", ""),
                    row.get("ubicacion_lat", ""),
                    row.get("ubicacion_lon", ""),
                    row.get("imagen_url"),
                    row.get("created_at"),
                ]
            )

        output.seek(0)
        headers = {
            "Content-Disposition": 'attachment; filename="dataset_plagas_validado.csv"'
        }
        return StreamingResponse(
            iter([output.getvalue()]), media_type="text/csv", headers=headers
        )
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar la exportación del CSV: {str(e)}",
        )