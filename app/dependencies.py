# app/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import settings
from app.database import supabase
from app.schemas import RolUsuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales o el token ha expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    response = supabase.table("usuarios").select("*").eq("email", email).execute()
    if not response.data:
        raise credentials_exception
    return response.data[0]

def require_roles(roles_permitidos: list[RolUsuario]):
    def role_checker(usuario_actual: dict = Depends(get_current_user)):
        rol_usuario = usuario_actual.get("rol")
        if rol_usuario not in [r.value for r in roles_permitidos]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los siguientes roles: {[r.value for r in roles_permitidos]}"
            )
        return usuario_actual
    return role_checker