from fastapi import APIRouter
from config import configure_logging
import cloudinary.api

router = APIRouter()
logger = configure_logging(__name__)

@router.get("/images")
def get_cloudinary_image_structure():
    logger.info("Fetching Cloudinary image structure.")
    genders = ["men", "women"]
    categories = ["classic", "superhero", "civilization", "fantasy"]
    structure = {}
    user_tempelets_count = 0
    for gender in genders:
        structure[gender] = {}
        for category in categories:
            prefixes = [
                f"media_uploads/{gender}/{category}",
                f"user_tempelets/{gender}/{category}"
            ]
            urls = []
            for prefix in prefixes:
                try:
                    logger.info("Fetching resources for prefix: %s", prefix)
                    resources = cloudinary.api.resources(
                        type="upload",
                        prefix=prefix,
                        resource_type="image",
                        max_results=100
                    )
                    urls_list = [res["secure_url"] for res in resources.get("resources", [])]
                    logger.info("Fetched %d images for prefix %s", len(urls_list), prefix)
                    urls.extend(urls_list)
                    if prefix.startswith("user_tempelets/"):
                        user_tempelets_count += len(urls_list)
                except Exception as e:
                    logger.exception("Error fetching images for %s: %s", prefix, e)
            structure[gender][category] = urls
    logger.info("Image structure fetched successfully. Total user_tempelets count: %d", user_tempelets_count)
    return {"structure": structure, "user_tempelets_count": user_tempelets_count}