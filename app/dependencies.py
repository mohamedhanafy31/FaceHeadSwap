from fastapi import HTTPException, Query, status
from config import configure_logging, db

logger = configure_logging(__name__)

# In-memory user storage (optional, for compatibility)
users_db = {}

def get_current_user(token: str = Query(...)):
    # Check Firestore for token
    users_ref = db.collection('users').where('token', '==', token).limit(1).stream()
    for user in users_ref:
        return user.id  # Email as document ID
    logger.warning("Invalid or expired token provided: %s", token)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")