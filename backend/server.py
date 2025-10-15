from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import random
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# LLM Integration
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# In-memory storage for simulation state
simulation_state = {
    "is_paused": False,
    "is_manual": False,
    "current_green": "north",
    "traffic_data": {
        "north": {"vehicles": 0, "signal": "red"},
        "south": {"vehicles": 0, "signal": "red"},
        "east": {"vehicles": 0, "signal": "red"},
        "west": {"vehicles": 0, "signal": "red"}
    },
    "insights": [],
    "cycle_count": 0
}

# Define Models
class TrafficUpdate(BaseModel):
    direction: str
    vehicles: int

class TrafficState(BaseModel):
    north: dict
    south: dict
    east: dict
    west: dict
    current_green: str
    is_paused: bool
    is_manual: bool
    cycle_count: int

class AIInsight(BaseModel):
    timestamp: str
    decision: str
    explanation: str
    vehicle_counts: dict

class ManualControl(BaseModel):
    direction: str

class ExplanationRequest(BaseModel):
    direction: str
    vehicle_count: int
    all_counts: dict

# Generate AI explanation using GPT-5
async def generate_ai_explanation(direction: str, vehicle_count: int, all_counts: dict) -> str:
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id="traffic-controller",
            system_message="You are an AI traffic management system. Provide clear, concise explanations for traffic signal decisions. Keep responses under 25 words."
        ).with_model("openai", "gpt-5")
        
        prompt = f"Traffic detected: North={all_counts['north']}, South={all_counts['south']}, East={all_counts['east']}, West={all_counts['west']} vehicles. The {direction} road has the highest congestion with {vehicle_count} vehicles. Explain why you're prioritizing this direction."
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return response
    except Exception as e:
        logging.error(f"Error generating AI explanation: {e}")
        return f"Prioritizing {direction} road with {vehicle_count} vehicles due to highest congestion."

@api_router.get("/")
async def root():
    return {"message": "AI Traffic Signal Controller API"}

@api_router.get("/traffic/current", response_model=TrafficState)
async def get_current_traffic():
    """Get current traffic state"""
    return TrafficState(
        north=simulation_state["traffic_data"]["north"],
        south=simulation_state["traffic_data"]["south"],
        east=simulation_state["traffic_data"]["east"],
        west=simulation_state["traffic_data"]["west"],
        current_green=simulation_state["current_green"],
        is_paused=simulation_state["is_paused"],
        is_manual=simulation_state["is_manual"],
        cycle_count=simulation_state["cycle_count"]
    )

@api_router.post("/traffic/update")
async def update_traffic():
    """Simulate new vehicle counts and determine signal states"""
    if simulation_state["is_paused"] or simulation_state["is_manual"]:
        return {"message": "Simulation paused or in manual mode"}
    
    # Generate random vehicle counts
    directions = ["north", "south", "east", "west"]
    vehicle_counts = {}
    
    for direction in directions:
        count = random.randint(0, 50)
        simulation_state["traffic_data"][direction]["vehicles"] = count
        vehicle_counts[direction] = count
    
    # Find direction with highest count
    max_direction = max(vehicle_counts, key=vehicle_counts.get)
    max_count = vehicle_counts[max_direction]
    
    # Update signal states
    for direction in directions:
        if direction == max_direction:
            simulation_state["traffic_data"][direction]["signal"] = "green"
        else:
            simulation_state["traffic_data"][direction]["signal"] = "red"
    
    simulation_state["current_green"] = max_direction
    simulation_state["cycle_count"] += 1
    
    # Generate AI explanation
    explanation = await generate_ai_explanation(max_direction, max_count, vehicle_counts)
    
    # Store insight (keep last 10)
    insight = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": f"Green light: {max_direction.upper()}",
        "explanation": explanation,
        "vehicle_counts": vehicle_counts
    }
    
    simulation_state["insights"].insert(0, insight)
    if len(simulation_state["insights"]) > 10:
        simulation_state["insights"] = simulation_state["insights"][:10]
    
    return {
        "traffic_data": simulation_state["traffic_data"],
        "current_green": max_direction,
        "insight": insight
    }

@api_router.get("/traffic/insights")
async def get_insights():
    """Get recent AI insights"""
    return {"insights": simulation_state["insights"]}

@api_router.post("/traffic/pause")
async def pause_simulation():
    """Pause the simulation"""
    simulation_state["is_paused"] = True
    return {"message": "Simulation paused", "is_paused": True}

@api_router.post("/traffic/resume")
async def resume_simulation():
    """Resume the simulation"""
    simulation_state["is_paused"] = False
    return {"message": "Simulation resumed", "is_paused": False}

@api_router.post("/traffic/manual")
async def set_manual_control(control: ManualControl):
    """Set manual control for a specific direction"""
    if control.direction not in ["north", "south", "east", "west"]:
        raise HTTPException(status_code=400, detail="Invalid direction")
    
    simulation_state["is_manual"] = True
    
    # Update signals manually
    for direction in ["north", "south", "east", "west"]:
        if direction == control.direction:
            simulation_state["traffic_data"][direction]["signal"] = "green"
        else:
            simulation_state["traffic_data"][direction]["signal"] = "red"
    
    simulation_state["current_green"] = control.direction
    
    return {
        "message": f"Manual control: {control.direction} set to green",
        "traffic_data": simulation_state["traffic_data"]
    }

@api_router.post("/traffic/auto")
async def set_auto_mode():
    """Return to automatic mode"""
    simulation_state["is_manual"] = False
    return {"message": "Switched to automatic mode", "is_manual": False}

@api_router.post("/traffic/reset")
async def reset_simulation():
    """Reset the simulation"""
    simulation_state["is_paused"] = False
    simulation_state["is_manual"] = False
    simulation_state["current_green"] = "north"
    simulation_state["cycle_count"] = 0
    simulation_state["insights"] = []
    
    for direction in ["north", "south", "east", "west"]:
        simulation_state["traffic_data"][direction] = {"vehicles": 0, "signal": "red"}
    
    return {"message": "Simulation reset", "traffic_data": simulation_state["traffic_data"]}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()