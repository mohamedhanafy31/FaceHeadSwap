from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from firebase_admin import firestore
import secrets
from passlib.context import CryptContext
from config import db
import logging
import os
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)  # Suppress bcrypt warnings
logger = logging.getLogger(__name__)

# Initialize FastAPI router and password hashing context
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic models for request validation
class UserRegister(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str
    deviceKey: str | None = None

class AutoLoginRequest(BaseModel):
    device_key: str

# Utility function to generate a random device key
def generate_device_key():
    return secrets.token_hex(16)

# User registration endpoint
@router.post("/register")
async def register(user: UserRegister):
    users_ref = db.collection('users')
    query = users_ref.where('email', '==', user.email).limit(1).stream()
    email_exists = any(query)

    if email_exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = pwd_context.hash(user.password)
    device_key = generate_device_key()
    token = secrets.token_hex(16)

    # User data with access set to False by default
    user_data = {
        "email": user.email,
        "password": hashed_password,
        "deviceKey": device_key,
        "name": user.name,
        "created_at": firestore.SERVER_TIMESTAMP,
        "token": token,
        "access": False  # Default access is restricted
    }

    # Store user data in Firestore
    user_ref = db.collection('users').document(user.email)
    user_ref.set(user_data)
    keys_ref = db.collection('keys').document('saved_keys')
    keys_ref.set({user.email: {"deviceKey": device_key, "name": user.name}}, merge=True)

    logger.info(f"User registered: {user.email}")
    return {"message": "User registered successfully", "token": token, "deviceKey": device_key}

# Directory to save login files
LOGIN_FILES_DIR = "login_logs"
os.makedirs(LOGIN_FILES_DIR, exist_ok=True)

# User login endpoint
@router.post("/login")
async def login(payload: UserLogin):
    email = payload.email
    password = payload.password
    device_key = payload.deviceKey

    # Retrieve user document from Firestore
    user_ref = db.collection("users").document(email)
    user_doc = user_ref.get()

    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = user_doc.to_dict()
    stored_password = user_data.get("password")

    # Migrate unhashed passwords (for backward compatibility)
    if not stored_password.startswith("$2b$"):  # Check if password is not bcrypt-hashed
        logger.warning(f"Unhashed password detected for {email}. Migrating...")
        hashed_password = pwd_context.hash(stored_password)
        user_ref.update({"password": hashed_password})
        stored_password = hashed_password

    # Verify password
    if not pwd_context.verify(password, stored_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check user access
    access = user_data.get("access", False)  # Default to False if field is missing
    if not access:
        logger.warning(f"Access denied for user: {email}")
        raise HTTPException(status_code=403, detail="You are not allowed, please contact the company")

    # Validate device key if provided
    if device_key:
        keys_ref = db.collection("keys").document("saved_keys")
        keys_doc = keys_ref.get()
        if not keys_doc.exists:
            raise HTTPException(status_code=500, detail="Keys configuration error")
        keys_data = keys_doc.to_dict()
        stored_device_key = keys_data.get(email, {}).get("deviceKey")
        if device_key != stored_device_key:
            raise HTTPException(status_code=401, detail="Device key mismatch")

    # Generate token
    token = secrets.token_hex(16)
    user_ref.update({"token": token})

    # Prepare login data
    login_entry = {
        "loginTimestamp": datetime.utcnow().isoformat(),
        "token": token,
        "email": email,
        "name": user_data.get("name", "")
    }

    # Save login data to a single JSON file per email
    filename = f"login.json"
    file_path = os.path.join(LOGIN_FILES_DIR, filename)

    try:
        # Read existing data or initialize an empty list
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                existing_data = json.load(f)
            if not isinstance(existing_data, list):
                existing_data = [existing_data]  # Convert old single-entry format to list
        else:
            existing_data = []

        # Append new login entry
        existing_data.append(login_entry)

        # Write updated data back to file
        with open(file_path, 'w') as f:
            json.dump(existing_data, f, indent=2)
        logger.info(f"Login info appended to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save login info to file: {str(e)}")
        # Optionally raise an exception if file saving is critical
        # raise HTTPException(status_code=500, detail="Failed to save login info")

    logger.info(f"User logged in: {email}")
    return {"message": "Login successful", "token": token, "email": email, "name": user_data.get("name", "")}

# Auto-login endpoint using device key
@router.post("/autologin")
async def autologin(payload: AutoLoginRequest):
    device_key = payload.device_key

    # Retrieve saved keys from Firestore
    keys_ref = db.collection("keys").document("saved_keys")
    keys_doc = keys_ref.get()
    if not keys_doc.exists:
        raise HTTPException(status_code=401, detail="No saved keys found")

    keys_data = keys_doc.to_dict()
    matched_email = None
    for email, data in keys_data.items():
        if data.get("deviceKey") == device_key:
            matched_email = email
            break

    if not matched_email:
        raise HTTPException(status_code=401, detail="Device key not recognized")

    # Retrieve user data
    user_ref = db.collection("users").document(matched_email)
    user_doc = user_ref.get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = user_doc.to_dict()
    # Check user access
    access = user_data.get("access", False)  # Default to False if field is missing
    if not access:
        logger.warning(f"Access denied for user: {matched_email}")
        raise HTTPException(status_code=403, detail="You are not allowed, please contact the company")

    # Generate and update token
    token = secrets.token_hex(16)
    user_ref.update({"token": token})
    logger.info(f"Auto-login successful for: {matched_email}")
    return {"message": "Auto login successful", "token": token, "email": matched_email, "name": user_data.get("name", "")}