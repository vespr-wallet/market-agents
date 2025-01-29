from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from crewai import Agent, Task, Crew
from dotenv import load_dotenv, find_dotenv
from masumi_crewai.config import Config
from masumi_crewai.payment import Payment, Amount

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Force reload of .env file
load_dotenv(find_dotenv(), override=True)

logger.info(f"Env file location: {find_dotenv()}")
logger.info("Environment variables after loading:")
for key in ['PAYMENT_SERVICE_URL', 'PAYMENT_API_KEY']:
    logger.info(f"{key}: {os.getenv(key)}")

def print_config():
    logger.info("=== Configuration ===")
    logger.info(f"PAYMENT_SERVICE_URL: {os.getenv('PAYMENT_SERVICE_URL')}")
    logger.info(f"PAYMENT_API_KEY: {os.getenv('PAYMENT_API_KEY')}")
    logger.info("==================")

print_config()

app = FastAPI()

# Storage setup
RESULTS_DIR = "job_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Track state
jobs: Dict[str, Dict[str, str]] = {}
payments: Dict[str, Payment] = {}
start_time = datetime.now()

# Initialize config once
config = Config(
    payment_service_url=os.getenv('PAYMENT_SERVICE_URL'),
    payment_api_key=os.getenv('PAYMENT_API_KEY')
)

# Pydantic models for request/response validation
class JobRequest(BaseModel):
    input_data: str

class JobResponse(BaseModel):
    job_id: str
    payment_id: str
    payment_address: str

class JobStatus(BaseModel):
    job_id: str
    payment_id: str
    status: str
    result: Optional[str] = None
    payment_status: Optional[str] = None

class AvailabilityResponse(BaseModel):
    status: str
    uptime: int

async def execute_crew_task(input_data: str) -> str:
    researcher = Agent(
        role='Research Analyst',
        goal='Find and analyze key information',
        backstory='Expert at extracting information',
        verbose=True
    )
    writer = Agent(
        role='Content Summarizer',
        goal='Create clear summaries from research',
        backstory='Skilled at transforming complex information',
        verbose=True
    )
    
    crew = Crew(
        agents=[researcher, writer],
        tasks=[
            Task(description=f'Research: {input_data}', agent=researcher),
            Task(description='Write summary', agent=writer)
        ]
    )
    return str(crew.kickoff())

async def handle_payment_status(job_id: str, status: Dict) -> None:
    logger.info(f"Handling payment status for job {job_id}")
    logger.info(f"Status received: {status}")
    
    payment_status = status.get("data", {}).get("status")
    logger.info(f"Payment status: {payment_status}")
    
    jobs[job_id]["payment_status"] = payment_status
    
    if payment_status == "CONFIRMED":
        logger.info(f"Payment confirmed for job {job_id}, starting crew task...")
        try:
            jobs[job_id]["status"] = "running"
            result = await execute_crew_task(jobs[job_id]["input_data"])
            logger.info(f"Crew task completed for job {job_id}")
            
            payment = payments[job_id]
            await payment.complete_payment(result[:64])
            logger.info(f"Payment completed for job {job_id}")
            
            output = {
                "result": result,
                "status": "completed",
                "payment_id": jobs[job_id]["payment_id"],
                "payment_status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            output = {
                "error": str(e),
                "status": "failed",
                "payment_id": jobs[job_id]["payment_id"],
                "payment_status": payment_status
            }
        
        # Save final result
        result_path = os.path.join(RESULTS_DIR, f"{job_id}.json")
        with open(result_path, 'w') as f:
            json.dump(output, f)
        jobs[job_id]["status"] = output["status"]
        logger.info(f"Saved results for job {job_id}")

@app.post("/start_job", response_model=JobResponse)
async def start_job(job_request: JobRequest):
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    logger.info(f"Starting new job with ID: {job_id}")
    logger.info(f"Input data: {job_request.input_data}")
    
    try:
        # Initialize payment
        logger.info("Initializing payment...")
        payment = Payment(
            agent_identifier=job_id,
            amounts=[Amount(amount=5000000, unit="lovelace")],
            config=config
        )
        
        # Create payment request
        logger.info("Creating payment request...")
        try:
            deadline = (now + timedelta(hours=10)).isoformat() + "Z"
            # Log the request data
            logger.info("Payment request data:")
            logger.info(f"- agent_identifier: {job_id}")
            logger.info(f"- amounts: [{Amount(amount=5000000, unit='lovelace')}]")
            logger.info(f"- deadline: {deadline}")
            logger.info(f"- payment_service_url: {config.payment_service_url}")
            
            payment_request = await payment.create_payment_request(deadline)
            logger.info(f"Payment request created: {payment_request}")
        except Exception as e:
            logger.error(f"Error creating payment request: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create payment request: {str(e)}"
            )
        
        # Store job info
        logger.info("Storing job information...")
        jobs[job_id] = {
            "status": "pending_payment",
            "payment_status": "pending",
            "payment_id": payment_request['data']['identifier'],
            "input_data": job_request.input_data
        }
        payments[job_id] = payment
        
        response = JobResponse(
            job_id=job_id,
            payment_id=payment_request['data']['identifier'],
            payment_address=payment_request['data']['payment_address']
        )
        logger.info(f"Returning response: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Unexpected error in start_job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.get("/status", response_model=JobStatus)
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_id in payments:
        # Update payment status
        status = await payments[job_id].check_payment_status()
        jobs[job_id]["payment_status"] = status.get("data", {}).get("status")
    
    result_path = os.path.join(RESULTS_DIR, f"{job_id}.json")
    if os.path.exists(result_path):
        with open(result_path, 'r') as f:
            data = json.load(f)
            return JobStatus(**data)
    
    return JobStatus(
        job_id=job_id,
        payment_id=jobs[job_id]["payment_id"],
        status=jobs[job_id]["status"],
        payment_status=jobs[job_id].get("payment_status", "unknown")
    )

@app.get("/availability", response_model=AvailabilityResponse)
async def check_availability():
    return AvailabilityResponse(
        status="available",
        uptime=int((datetime.now() - start_time).total_seconds())
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 