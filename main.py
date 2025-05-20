#uvicorn main:app --reload

from fastapi import FastAPI
import motor.motor_asyncio
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models import User, UserCreate, UserLogin
from auth import hash_password, verify_password, create_access_token, decode_access_token
from datetime import datetime

app = FastAPI()

# MongoDB connection
MONGO_URL = "mongodb://localhost:27017"  # if you have MongoDB running locally
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client.chatbot_db  # This will create a database called "chatbot_db" automatically

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Health Check Endpoint
@app.get("/health-check")
async def health_check():
    return {"status": "ok"}


# Signup Route
@app.post("/signup")
async def signup(user: UserCreate):
    existing_user = await db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    user_dict = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hash_password(user.password),
        "created_at": datetime.utcnow()
    }
    await db.users.insert_one(user_dict)
    return {"message": "User created successfully"}

# Login Route
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.users.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    return {"access_token": access_token, "token_type": "bearer"}

# Dependency to get current user
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    user_id = payload.get("sub")
    user = await db.users.find_one({"_id": motor.motor_asyncio.AsyncIOMotorClient().get_default_database().users.ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
