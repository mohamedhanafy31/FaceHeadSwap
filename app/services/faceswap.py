import cv2
import numpy as np
import tempfile
import os
import torch
from fastapi import HTTPException
import onnxruntime as ort
from config import configure_logging

logger = configure_logging(__name__)



def process_face_swap(source_img: np.ndarray, target_img: np.ndarray, face_swapper, face_analyzer) -> np.ndarray:
    logger.info("Starting face swap process with InSwapper")
    source_faces = face_analyzer.get(source_img)
    if not source_faces:
        logger.error("No faces detected in source image")
        raise ValueError("No faces detected in source image")
    target_faces = face_analyzer.get(target_img)
    if not target_faces:
        logger.error("No faces detected in target image")
        raise ValueError("No faces detected in target image")
    result = target_img.copy()
    for face in target_faces:
        logger.info("Swapping face with target face bbox: %s", getattr(face, "bbox", "unknown"))
        result = face_swapper.get(result, face, source_faces[0], paste_back=True)
    
    
    logger.info("Face swap process completed successfully")
    return result

def process_head_swap(src_bytes, tgt_bytes, headswap_model):
    logger.info("Processing source and target images for HeadSwap")
    src_array = np.frombuffer(src_bytes, np.uint8)
    tgt_array = np.frombuffer(tgt_bytes, np.uint8)
    src_img = cv2.imdecode(src_array, cv2.IMREAD_COLOR)
    tgt_img = cv2.imdecode(tgt_array, cv2.IMREAD_COLOR)
    if src_img is None or tgt_img is None:
        logger.error("One or both images could not be decoded")
        raise HTTPException(status_code=400, detail="One or both images could not be decoded")
    
    src_temp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tgt_temp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    src_temp_name = src_temp.name
    tgt_temp_name = tgt_temp.name
    src_temp.close()
    tgt_temp.close()
    
    try:
        if not cv2.imwrite(src_temp_name, src_img):
            logger.error("Failed to write source image")
            raise HTTPException(status_code=500, detail="Failed to write source image")
        if not cv2.imwrite(tgt_temp_name, tgt_img):
            logger.error("Failed to write target image")
            raise HTTPException(status_code=500, detail="Failed to write target image")
        
        logger.info("Running HeadSwap model")
        result_img = headswap_model.run_single(src_temp_name, tgt_temp_name, crop_align=True, cat=True)
        
        logger.info("HeadSwap processing completed successfully")
        return result_img
    
    except Exception as e:
        logger.exception(f"Error processing images: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.remove(src_temp_name)
            os.remove(tgt_temp_name)
        except Exception as e:
            logger.warning(f"Error removing temporary files: {str(e)}")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def convert_to_landscape(img, target_size=(1920, 1080)):
    logger.info("Converting image to landscape with target_size: %s", target_size)
    return cv2.resize(img, target_size)