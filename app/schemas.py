# app/schemas.py

from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from enum import Enum

# Tipos de Producción
class TipoProduccion(str, Enum):
    EXTENSIVO = "EXTENSIVO"
    INTENSIVO = "INTENSIVO"

# Estados del Hallazgo
class EstadoValidacion(str, Enum):
    PENDIENTE = "PENDIENTE"
    VALIDADO = "VALIDADO"
    RECHAZADO = "RECHAZADO"

# Roles de Usuario
class RolUsuario(str, Enum):
    PRODUCTOR = "PRODUCTOR"
    AGRONOMO = "AGRONOMO"
    ADMIN = "ADMIN"

# Esquema para crear un nuevo usuario
class UsuarioCreate(BaseModel):
    nombre: str
    email: str
    password: str

# Esquema para que el ADMIN gestione roles
class CambiarRolIn(BaseModel):
    nuevo_rol: RolUsuario

class UsuarioOut(BaseModel):
    id: str
    nombre: str
    email: str
    rol: RolUsuario
    created_at: datetime

    class Config:
        from_attributes = True

class LoginIn(BaseModel):
    email: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut

# Esquema para responder datos de un hallazgo
class HallazgoOut(BaseModel):
    id: str
    created_at: datetime
    tipo_agro: TipoProduccion
    cultivo: str
    parte_afectada: Optional[str] = None
    imagen_url: str
    origen_carga: str
    observacion_usuario: Optional[str] = None
    ubicacion_lat: Optional[float] = None
    ubicacion_lon: Optional[float] = None
    estado: EstadoValidacion
    etiqueta_experto: Optional[str] = None
    observacion_experto: Optional[str] = None

    class Config:
        from_attributes = True

#  Solicitud de validación enviada por el experto agrónomo
class ValidacionExpertoIn(BaseModel):
    estado: EstadoValidacion  # Debe ser VALIDADO o RECHAZADO
    etiqueta_experto: str     # Ej: "Spodoptera frugiperda", "Alternaria leaf spot", etc.
    observacion_experto: Optional[str] = None # Ej: "Sintomatología clara de hongo fitopatógeno"

#  Solicitud de rechazo enviada por el experto agrónomo
class RechazoSchema(BaseModel):
    motivo_rechazo: str

class DatasetPaginadoOut(BaseModel):
    pagina_actual: int
    limite_por_pagina: int
    total_registros: int
    total_paginas: int
    datos: List[dict] 