from fastapi import APIRouter, Depends, UploadFile, File, status, HTTPException
from src.dependencies import get_current_seller
from services import file_service
from services.exceptions import InvalidFileType, FileTooLarge
from schemas.upload import UploadResponse

upload_router = APIRouter(prefix="/upload", tags=["Upload"])

@upload_router.post(
    "/image", response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузить изображение",
)
async def upload_image_endpoint(
    file: UploadFile = File(...),
    _=Depends(get_current_seller)
):
    try:
        url = await file_service.upload_image(file)
        return UploadResponse(url=url)
    except InvalidFileType as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileTooLarge as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))