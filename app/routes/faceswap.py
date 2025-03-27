from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from config import configure_logging, db
from firebase_admin import firestore  # Already imported for SERVER_TIMESTAMP
from dependencies import get_current_user
from services.faceswap import process_face_swap, process_head_swap, convert_to_landscape
from services.cloudinary import upload_to_cloudinary
import io
import cv2
import numpy as np
import qrcode
import base64
import cloudinary

router = APIRouter()
logger = configure_logging(__name__)

@router.post("/swap-face")
async def swap_face(
    request: Request,
    source: UploadFile = File(...),
    target: UploadFile = File(...),
    mode: str = Query("portrait", enum=["portrait", "landscape"]),
    model: str = Query("inswapper", enum=["inswapper", "headswap"]),
    return_type: str = Query("direct", enum=["direct", "qr"]),
    current_user: str = Depends(get_current_user)
):
    logger.info(f"swap-face endpoint called with model: {model}, mode: {mode}, return_type: {return_type}")
    source_bytes = await source.read()
    target_bytes = await target.read()
    logger.info(f"Received source image ({len(source_bytes)} bytes) and target image ({len(target_bytes)} bytes).")
    
    try:
        if model == "inswapper":
            face_swapper = request.app.state.face_swapper
            face_analyzer = request.app.state.face_analyzer
            if face_swapper is None or face_analyzer is None:
                logger.error("InSwapper model or analyzer not available.")
                raise HTTPException(status_code=501, detail="InSwapper model not available")
            source_img = cv2.imdecode(np.frombuffer(source_bytes, np.uint8), cv2.IMREAD_COLOR)
            target_img = cv2.imdecode(np.frombuffer(target_bytes, np.uint8), cv2.IMREAD_COLOR)
            if source_img is None or target_img is None:
                raise HTTPException(status_code=400, detail="Failed to decode images")
            result_img = process_face_swap(source_img, target_img, face_swapper, face_analyzer)
        elif model == "headswap":
            headswap_model = request.app.state.headswap_model
            if headswap_model is None:
                logger.error("HeadSwap model not available.")
                raise HTTPException(status_code=501, detail="HeadSwap model not available")
            result_img = process_head_swap(source_bytes, target_bytes, headswap_model)
        else:
            raise HTTPException(status_code=400, detail="Invalid model selection")
        
        if mode == "landscape":
            result_img = convert_to_landscape(result_img)
        
        if return_type == "direct":
            success, encoded_image = cv2.imencode(".png", result_img)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to encode result image")
            return StreamingResponse(io.BytesIO(encoded_image.tobytes()), media_type="image/png")
        
        elif return_type == "qr":
            _, img_encoded = cv2.imencode('.jpg', result_img)
            img_bytes = img_encoded.tobytes()
            folder = f"face_swap_results/{model}"
            upload_result = upload_to_cloudinary(img_bytes, folder)
            secure_url = upload_result.get("secure_url", "").replace("/upload/", "/upload/fl_attachment/")
            
            result_ref = db.collection('face_swaps').document()
            result_ref.set({
                "user": current_user,
                "model": model,
                "mode": mode,
                "image_url": secure_url,
                "created_at": firestore.SERVER_TIMESTAMP  # Corrected: no parentheses
            })
            logger.info("Face swap result stored in Firestore for user: %s", current_user)
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(secure_url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill="black", back_color="white")
            buf = io.BytesIO()
            qr_img.save(buf, format="PNG")
            qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            return JSONResponse({
                "swapped_image_url": secure_url,
                "qr_code": f"data:image/png;base64,{qr_base64}",
                "model_used": model
            })
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception("Unexpected error in face/head swap process: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# Rest of the file remains unchanged (swap-face-qr, headswap, headswap-qr endpoints)
@router.post("/swap-face-qr/")
async def swap_face_qr(
    request: Request,
    source: UploadFile = File(...),
    target: UploadFile = File(...),
    mode: str = Query("portrait", enum=["portrait", "landscape"])
):
    logger.info(f"swap-face-qr endpoint called with mode: {mode}")
    source_bytes = await source.read()
    target_bytes = await target.read()
    logger.info(f"Received source image ({len(source_bytes)} bytes) and target image ({len(target_bytes)} bytes).")
    
    face_swapper = request.app.state.face_swapper
    face_analyzer = request.app.state.face_analyzer
    if face_swapper is None or face_analyzer is None:
        logger.error("InSwapper model or analyzer not available.")
        raise HTTPException(status_code=501, detail="InSwapper model not available")
    
    try:
        source_img = cv2.imdecode(np.frombuffer(source_bytes, np.uint8), cv2.IMREAD_COLOR)
        target_img = cv2.imdecode(np.frombuffer(target_bytes, np.uint8), cv2.IMREAD_COLOR)
        if source_img is None or target_img is None:
            logger.error("Failed to decode source or target image.")
            raise HTTPException(status_code=400, detail="Failed to decode images")

        result_img = process_face_swap(source_img, target_img, face_swapper, face_analyzer)

        _, img_encoded = cv2.imencode('.jpg', result_img)
        img_bytes = img_encoded.tobytes()

        folder = "face_swap_results/inswapper"
        upload_result = cloudinary.uploader.upload(
            file=io.BytesIO(img_bytes),
            folder=folder,
            resource_type="image"
        )
        secure_url = upload_result.get("secure_url", "").replace("/upload/", "/upload/fl_attachment/")

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(secure_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill="black", back_color="white")
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        logger.info("Face swap completed. Returning URL and QR code.")
        return {
            "swapped_image_url": secure_url,
            "qr_code": f"data:image/png;base64,{qr_base64}",
            "model_used": "inswapper"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(f"Error in swap-face-qr: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/headswap")
async def headswap(
    request: Request,
    source: UploadFile = File(...),
    target: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    headswap_model = request.app.state.headswap_model
    if headswap_model is None:
        logger.error("HeadSwap model not available.")
        raise HTTPException(status_code=501, detail="HeadSwap model not available")
    return await swap_face(request, source, target, mode="portrait", model="headswap", return_type="direct", current_user=current_user)

@router.post("/headswap-qr")
async def headswap_qr(
    request: Request,
    source: UploadFile = File(...),
    target: UploadFile = File(...),
    mode: str = Query("portrait", enum=["portrait", "landscape"]),
    current_user: str = Depends(get_current_user)
):
    headswap_model = request.app.state.headswap_model
    if headswap_model is None:
        logger.error("HeadSwap model not available.")
        raise HTTPException(status_code=501, detail="HeadSwap model not available")
    return await swap_face(request, source, target, mode=mode, model="headswap", return_type="qr", current_user=current_user)