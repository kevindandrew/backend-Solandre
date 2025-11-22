from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class LoginRequest(BaseModel):
    """Schema para la solicitud de login"""
    email: EmailStr
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    """Schema para el registro de un nuevo usuario (Cliente)"""
    nombre_completo: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)


class TokenResponse(BaseModel):
    """Schema para la respuesta del token de acceso"""
    access_token: str
    token_type: str = "bearer"
    usuario_id: int
    rol_id: int
    nombre_completo: str
    email: str


class UserResponse(BaseModel):
    """Schema para la respuesta de datos del usuario"""
    usuario_id: int
    nombre_completo: str
    email: str
    telefono: Optional[str]
    rol_id: int
    nombre_rol: str

    class Config:
        from_attributes = True


class ActualizarPerfilRequest(BaseModel):
    """Schema para actualizar el perfil del usuario"""
    nombre_completo: Optional[str] = Field(None, min_length=2, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)


class CambiarPasswordRequest(BaseModel):
    """Schema para cambiar la contraseña"""
    password_actual: str = Field(..., min_length=6)
    password_nueva: str = Field(..., min_length=6)
