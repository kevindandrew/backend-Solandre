from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
import cloudinary
import cloudinary.uploader
from app.config import settings
from app.utils.dependencies import verificar_admin

router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
    responses={404: {"description": "Not found"}},
)

# Configuración de Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

@router.post("/image", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verificar_admin)])
async def upload_image(file: UploadFile = File(...)):
    """
    Sube una imagen a Cloudinary y devuelve la URL segura.
    """
    try:
        # Validar tipo de archivo (opcional pero recomendado)
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo debe ser una imagen"
            )

        # Subir a Cloudinary
        # file.file es un objeto SpooledTemporaryFile que Cloudinary puede leer
        result = cloudinary.uploader.upload(file.file)
        
        return {
            "url": result.get("secure_url"),
            "public_id": result.get("public_id")
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir la imagen: {str(e)}"
        )
