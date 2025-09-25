from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import csv
from datetime import datetime
import os
from supabase import create_client, Client
from typing import Optional
from fastapi import Query

# --- Supabase setup ---
SUPABASE_URL = "https://jhpzhyzdikpfoiblvuzv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpocHpoeXpkaWtwZm9pYmx2dXp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg3MjM3NTYsImV4cCI6MjA3NDI5OTc1Nn0.YBZv3NFuioenyzu7BKm_yyRQO0D3IMR7YusoRbAgkWc"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


app = FastAPI()
CSV_FILE = "reservations.csv"

# Ensure CSV file exists with headers
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["name", "contact_info", "guests", "date", "time"])

# Pydantic model for reservation input
class Reservation(BaseModel):
    name: str
    contact_info: str
    guests: int
    date: str  # Format: YYYY-MM-DD
    time: str  # Format: HH:MM (24-hour)



# Helper function to check availability
def is_available(date: str, time: str) -> bool:
    with open(CSV_FILE, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["date"] == date and row["time"] == time:
                return False
    return True

# --- Pydantic models ---
class Customer(BaseModel):
    name: str
    contact: str
    guests: int

class Booking(BaseModel):
    name: str
    contact: str
    date: str  # YYYY-MM-DD
    time: str  # HH:MM

class Conversation(BaseModel):
    customer_id: int
    category: str
    intent: str
    transcript: str
    sentiment: Optional[str] = None
    challenges: Optional[str] = None
    customer_ratings: Optional[int] = Field(None, ge=1, le=5)



# --- Routes ---
@app.post("/reservation")
def add_reservation(reservation: Reservation):
    if not is_available(reservation.date, reservation.time):
        return {"success": False, "message": "Slot not available"}
    
    with open(CSV_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            reservation.name,
            reservation.contact_info,
            reservation.guests,
            reservation.date,
            reservation.time
        ])
    return {"success": True, "message": "Reservation added successfully"}

@app.get("/availability")
def check_availability(date: str, time: str):
    available = is_available(date, time)
    return {"available": available}



@app.post("/customer")
def add_customer(customer: Customer):
    response = supabase.table("customers").insert({
        "name": customer.name,
        "contact": customer.contact,
        "guests": customer.guests
    }).execute()

    print(response)
    
    if response.status_code != 201:
        raise HTTPException(status_code=400, detail="Failed to add customer")
    
    return {"success": True, "message": "Customer added"}

@app.post("/booking")
def add_booking(booking: Booking):
    response = supabase.table("bookings").insert({
        "name": booking.name,
        "contact": booking.contact,
        "date": booking.date,
        "time": booking.time
    }).execute()
    
    if response.status_code != 201:
        raise HTTPException(status_code=400, detail="Failed to add booking")
    
    return {"success": True, "message": "Booking added"}

# --- Route to add conversation ---
@app.post("/conversation")
def add_conversation(conversation: Conversation):
    # Check if customer exists
    customer_check = supabase.table("customers").select("*").eq("id", conversation.customer_id).execute()
    if not customer_check.data or len(customer_check.data) == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Insert conversation
    response = supabase.table("conversations").insert({
        "customer_id": conversation.customer_id,
        "category": conversation.category,
        "intent": conversation.intent,
        "transcript": conversation.transcript,
        "sentiment": conversation.sentiment,
        "challenges": conversation.challenges,
        "customer_ratings": conversation.customer_ratings
    }).execute()
    
    if response.status_code != 201:
        raise HTTPException(status_code=400, detail="Failed to add conversation")
    
    return {"success": True, "message": "Conversation added successfully", "conversation_id": response.data[0]["conversation_id"]}


@app.get("/conversation")
def get_conversation(customer_id: int = Query(None), conversation_id: int = Query(None)):
    query = supabase.table("conversations").select("*")

    if customer_id:
        query = query.eq("customer_id", customer_id)
    if conversation_id:
        query = query.eq("conversation_id", conversation_id)
    
    response = query.execute()
    
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch conversations")
    
    if not response.data:
        raise HTTPException(status_code=404, detail="No conversations found")
    
    return {"success": True, "conversations": response.data}
