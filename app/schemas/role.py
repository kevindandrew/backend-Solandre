from pydantic import BaseModel


class RoleResponse(BaseModel):
    rol_id: int
    nombre_rol: str

    class Config:
        from_attributes = True
