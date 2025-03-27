import sys
import logging
from pathlib import Path
import socket
from contextlib import asynccontextmanager
import torch
import firebase_admin
from firebase_admin import credentials, firestore
import cloudinary
import os
import uuid
import hashlib

def configure_logging(name: str) -> logging.Logger:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[logging.StreamHandler()]
    )
    logging.getLogger("uvicorn.error").propagate = False
    try:
        import insightface
        logging.getLogger("insightface").setLevel(logging.WARNING)
    except ImportError:
        pass
    logger = logging.getLogger(name)
    logger.info("Logging configuration complete.")
    return logger

# Initialize logger once at module level
logger = configure_logging(__name__)

def get_base_path() -> Path:
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent.parent  # Adjust for app directory
    logger.debug("Determined base path: %s", base_path)
    return base_path

def find_available_port(start_port=8000, max_port=9000) -> int:
    logger.info("Searching for available ports between %d and %d", start_port, max_port)
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                logger.info("Available port found: %d", port)
                return port
    logger.error("No available ports found between %d and %d", start_port, max_port)
    raise RuntimeError("No available ports found")

# Model Paths
current_dir = os.path.dirname(os.path.abspath(__file__))
inswapper_model_path = str(get_base_path()/ 'app' / 'model' / 'inswapper_128.onnx')
headswap_path = str(get_base_path() / 'app' / "HeadSwap")
if headswap_path not in sys.path:
    sys.path.insert(0, headswap_path)
    logger.info(f"Added HeadSwap path to sys.path: {headswap_path}")

HEADSWAP_MODEL_PATHS = {
    "checkpoint": os.path.join(headswap_path, "pretrained_models/epoch_00190_iteration_000400000_checkpoint.pt"),
    "blender": os.path.join(headswap_path, "pretrained_models/Blender-401-00012900.pth"),
    "parsing": os.path.join(headswap_path, "pretrained_models/parsing.pth"),
    "epoch": os.path.join(headswap_path, "pretrained_models/epoch_20.pth"),
    "bfm": os.path.join(headswap_path, "pretrained_models/BFM")
}

# Cloudinary Configuration
cloudinary.config(
    cloud_name="dj3ewvbqm",
    api_key="168548754285954",
    api_secret="3EuyZu2aeVwvGXv-obad0DKephc",
    secure=True
)
logger.info("Cloudinary configured successfully.")

# Firebase Initialization
cred = credentials.Certificate("app/remmabooth-ai-firebase-adminsdk-fbsvc-b8bae9300c.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
logger.info("Firebase Firestore initialized successfully.")

# Model Initialization Variables
face_swapper = None
face_analyzer = None
headswap_model = None

@asynccontextmanager
async def lifespan(app):
    global face_swapper, face_analyzer, headswap_model
    logger.setLevel(logging.INFO)
    logger.info("Application startup initiated.")
    
    try:
        logger.info("Starting initialization of InSwapper face swapper model...")
        import insightface
        import onnxruntime as ort
        providers = ['CPUExecutionProvider']
        if hasattr(ort, 'get_available_providers') and 'CUDAExecutionProvider' in ort.get_available_providers():
            providers.insert(0, 'CUDAExecutionProvider')
        logger.debug("Using execution providers: %s", providers)
        logger.info("Checking model file at: %s", inswapper_model_path)
        if not os.path.exists(inswapper_model_path):
            logger.error("InSwapper model file not found: %s", inswapper_model_path)
            raise FileNotFoundError(f"InSwapper model file not found: {inswapper_model_path}")
        face_swapper = insightface.model_zoo.get_model(inswapper_model_path, providers=providers)
        logger.info("Initializing face analyzer...")
        face_analyzer = insightface.app.FaceAnalysis()
        face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
        app.state.face_swapper = face_swapper
        app.state.face_analyzer = face_analyzer
        logger.info("InSwapper model and face analyzer loaded successfully.")
    except Exception as e:
        logger.exception("InSwapper model initialization failed: %s", str(e))
        logger.warning("InSwapper functionality will be disabled.")
        app.state.face_swapper = None
        app.state.face_analyzer = None

    try:
        logger.info("Starting initialization of HeadSwap model...")
        from HeadSwap.inference import Infer
        headswap_model = Infer(
            HEADSWAP_MODEL_PATHS["checkpoint"],
            HEADSWAP_MODEL_PATHS["blender"],
            HEADSWAP_MODEL_PATHS["parsing"],
            HEADSWAP_MODEL_PATHS["epoch"],
            HEADSWAP_MODEL_PATHS["bfm"]
        )
        app.state.headswap_model = headswap_model
        logger.info("HeadSwap model initialized successfully.")
    except Exception as e:
        logger.exception("HeadSwap model initialization failed: %s", str(e))
        logger.warning("HeadSwap functionality will be disabled.")
        app.state.headswap_model = None

    if app.state.face_swapper is None and app.state.headswap_model is None:
        logger.error("Failed to initialize any model. Application cannot function.")
        raise RuntimeError("All model initializations failed")
    else:
        logger.info("Model initialization completed. InSwapper: %s, HeadSwap: %s",
                    "available" if app.state.face_swapper else "not available",
                    "available" if app.state.headswap_model else "not available")

    yield

    logger.info("Application shutdown initiated. Clearing resources...")
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("Resources cleared. Application shutdown complete.")

def generate_secret_key():
    """Generate a secret key based on the device's MAC address."""
    mac_address = hex(uuid.getnode())[2:].upper()  # Remove "0x" and convert to uppercase
    secret_key = hashlib.sha256(mac_address.encode()).hexdigest()
    logger.info("Generated secret key: %s", secret_key)
    return secret_key