from fastapi import APIRouter
from config import configure_logging, face_swapper, headswap_model
import torch
import time

router = APIRouter()
logger = configure_logging(__name__)

@router.get("/heartbeat")
def heartbeat():
    logger.info("Heartbeat endpoint requested.")
    return {
        "status": "ok",
        "timestamp": time.time(),
        "gpu_available": torch.cuda.is_available(),
        "inswapper_available": face_swapper is not None,
        "headswap_available": headswap_model is not None
    }