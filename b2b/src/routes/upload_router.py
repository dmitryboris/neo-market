from fastapi import APIRouter, Depends, UploadFile, File, status, HTTPException
from src.dependencies import get_current_user
from src.services import file_service
from src.services.exceptions import InvalidFileType, FileTooLarge
from src.schemas.upload import UploadResponse

upload_router = APIRouter(prefix="/upload", tags=["Upload"])

@upload_router.post(
    "/image", response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload image",
)
async def upload_image_endpoint(
    file: UploadFile = File(...),
    _=Depends(get_current_user)
):
    try:
        url = await file_service.upload_image(file)
        return UploadResponse(url=url)
    except InvalidFileType as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileTooLarge as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))