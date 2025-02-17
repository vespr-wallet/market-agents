import os
import uvicorn
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from masumi_crewai.config import Config
from masumi_crewai.payment import Payment, Amount
from crew_definition import ResearchCrew

# Load environment variables
load_dotenv()

# Retrieve API Keys and URLs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL")
PAYMENT_API_KEY = os.getenv("PAYMENT_API_KEY")

# Initialize FastAPI
app = FastAPI()

# ─────────────────────────────────────────────────────────────────────────────
# Temporary in-memory job store (DO NOT USE IN PRODUCTION)
# ─────────────────────────────────────────────────────────────────────────────
jobs = {}
payment_instances = {}

# ─────────────────────────────────────────────────────────────────────────────
# Initialize Masumi Payment Config
# ─────────────────────────────────────────────────────────────────────────────
config = Config(
    payment_service_url=PAYMENT_SERVICE_URL,
    payment_api_key=PAYMENT_API_KEY
)

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────
class StartJobRequest(BaseModel):
    text: str

class ProvideInputRequest(BaseModel):
    job_id: str

# ─────────────────────────────────────────────────────────────────────────────
# CrewAI Task Execution
# ─────────────────────────────────────────────────────────────────────────────
async def execute_crew_task(input_data: str) -> str:
    """ Execute a CrewAI task with Research and Writing Agents """
    crew = ResearchCrew()
    result = crew.crew.kickoff({"text": input_data})
    return result

# ─────────────────────────────────────────────────────────────────────────────
# 1) Start Job (MIP-003: /start_job)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/start_job")
async def start_job(data: StartJobRequest):
    """ Initiates a job and creates a payment request """
    job_id = str(uuid.uuid4())
    agent_identifier = "dcdf2c533510e865e3d7e0f0e5537c7a176dd4dc1df69e83a703976b16a51f4536884829c1156cdb1110c1a70c0f97ff06036083f7e23a1346418517"

    # Create a payment request using Masumi
    payment = Payment(
        agent_identifier=agent_identifier,
        amounts=[Amount(amount="2000000", unit="lovelace")],  # 2 ADA as example
        config=config
    )
    
    payment_request = await payment.create_payment_request()
    payment_id = payment_request["data"]["blockchainIdentifier"]
    payment.payment_ids.add(payment_id)

    # Store job info (Awaiting payment)
    jobs[job_id] = {
        "status": "awaiting_payment",
        "payment_status": "pending",
        "payment_id": payment_id,
        "input_data": data.text,
        "result": None
    }

    async def payment_callback(payment_id: str):
        await handle_payment_status(job_id, payment_id)

    # Start monitoring the payment status
    payment_instances[job_id] = payment
    await payment.start_status_monitoring(payment_callback)

    return {
        "job_id": job_id,
        "payment_id": payment_id,
        "status": "awaiting_payment"
    }

# ─────────────────────────────────────────────────────────────────────────────
# 2) Process Payment and Execute AI Task
# ─────────────────────────────────────────────────────────────────────────────
async def handle_payment_status(job_id: str, payment_id: str) -> None:
    """ Executes CrewAI task after payment confirmation """
    result = await execute_crew_task(jobs[job_id]["input_data"])
    print(f"Crew task completed for job {job_id}")

    # Mark payment as completed on Masumi
    await payment_instances[job_id].complete_payment(payment_id, result[:64])
    print(f"Payment completed for job {job_id}")

    # Update job status
    jobs[job_id]["status"] = "completed"
    jobs[job_id]["payment_status"] = "completed"
    jobs[job_id]["result"] = result

    # Stop monitoring payment status
    if job_id in payment_instances:
        payment_instances[job_id].stop_status_monitoring()
        del payment_instances[job_id]

# ─────────────────────────────────────────────────────────────────────────────
# 3) Check Job and Payment Status (MIP-003: /status)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/status")
async def get_status(job_id: str):
    """ Retrieves the current status of a specific job """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Check latest payment status
    if job_id in payment_instances:
        status = await payment_instances[job_id].check_payment_status()
        job["payment_status"] = status.get("data", {}).get("status")

    return {
        "job_id": job_id,
        "status": job["status"],
        "payment_status": job["payment_status"],
        "result": job.get("result")
    }

# ─────────────────────────────────────────────────────────────────────────────
# 4) Check Server Availability (MIP-003: /availability)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/availability")
async def check_availability():
    """ Checks if the server is operational """
    return {
        "status": "available",
        "message": "The server is running smoothly."
    }

# ─────────────────────────────────────────────────────────────────────────────
# Main Logic if Called as a Script
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("Running CrewAI as standalone script is not supported when using payments.")
    print("Start the API using `python main.py api` instead.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        print("Starting FastAPI server with Masumi integration...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        main()
