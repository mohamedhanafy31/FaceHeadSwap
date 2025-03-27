from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import argparse
import os
from config import lifespan  # Import lifespan from config.py

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(lifespan=lifespan)  # Use lifespan from config.py

from routes.images import router as images_router
app.include_router(images_router, prefix="/api")

from routes.faceswap import router as faceswap_router
app.include_router(faceswap_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware configured successfully")

# Mount static files (relative to main.py's location)
static_dir = os.path.join(os.path.dirname(__file__), "..", "pages")
static_dir = os.path.abspath(static_dir)  # Ensure absolute path
logger.info(f"Mounting static files from: {static_dir}")
if not os.path.exists(static_dir):
    logger.error(f"Static directory {static_dir} does not exist")
    raise RuntimeError(f"Static directory '{static_dir}' does not exist")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
logger.info("Static files mounted at /static")

from routes.auth import router as auth_router
app.include_router(auth_router, prefix="/api")

@app.get("/api/heartbeat")
async def heartbeat():
    logger.info("Heartbeat endpoint requested.")
    return {
        "status": "ok",
        "inswapper_available": app.state.face_swapper is not None,
        "headswap_available": app.state.headswap_model is not None
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the FastAPI server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()

    logger.info(f"Starting FastAPI application on port {args.port}")
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")