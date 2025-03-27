import io
from config import configure_logging
from cloudinary import uploader

logger = configure_logging(__name__)

def upload_to_cloudinary(img_bytes, folder):
    logger.info("Uploading image to Cloudinary in folder: %s", folder)
    upload_result = uploader.upload(
        file=io.BytesIO(img_bytes),
        folder=folder,
        resource_type="image"
    )
    logger.info("Image uploaded successfully. Cloudinary response: %s", upload_result)
    return upload_result