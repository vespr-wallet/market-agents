"""
FastAPI service that integrates CrewAI with Masumi payment system.
This service allows users to:
1. Submit AI tasks that require payment
2. Process payments using the Masumi payment system
3. Execute CrewAI tasks once payment is confirmed
4. Check status of jobs and payments
"""

from fastapi import FastAPI, HTTPException
import uuid
import json
import os
from typing import Dict
from dotenv import load_dotenv, find_dotenv
from masumi_crewai.config import Config
from masumi_crewai.payment import Payment, Amount
from crew_executor import CrewExecutor

load_dotenv(find_dotenv(), override=True)

app = FastAPI(
    title="CrewAI Payment Service",
    description="Service for running CrewAI tasks with Masumi payment integration",
    version="1.0.0"
)

# Storage setup for job results
RESULTS_DIR = "job_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# In-memory storage
jobs: Dict[str, Dict[str, str]] = {}
payment_instances: Dict[str, Payment] = {}

# Initialize Masumi payment config
config = Config(
    payment_service_url=os.getenv('PAYMENT_SERVICE_URL'),
    payment_api_key=os.getenv('PAYMENT_API_KEY')
)

# Initialize CrewExecutor
crew_executor = CrewExecutor()

async def execute_crew_task(input_data: str) -> str:
    """
    Execute a CrewAI task with researcher and writer agents.
    
    Args:
        input_data: The research query or task description
        
    Returns:
        str: The final result from the CrewAI agents
    """
    return await crew_executor.execute_task(input_data)

@app.get("/availability")
async def check_availability():
    return {
        "status": "available"
    }

@app.get("/input_schema")
async def get_input_schema():
    return {
        "input_data": [
            { "key": "text", "value": "string" }
        ]
    }

@app.post("/start_job")
async def start_job(request: dict):
    job_id = str(uuid.uuid4())
    agent_identifier = "60d44b00e5a4f34867196160c22aa0308e710f13f9754d98f6ed6ad9180cc1c0c540d81b4983cf07306ed9e627f688f8ce4a5f88f12e00448765048e"
    
    payment = Payment(
        agent_identifier=agent_identifier,
        amounts=[Amount(amount=2000000, unit="lovelace")],
        config=config
    )
    
    payment_request = await payment.create_payment_request()
    payment_id = payment_request['data']['blockchainIdentifier']
    payment.payment_ids.add(payment_id)
    
    async def payment_callback(payment_id: str):
        await handle_payment_status(job_id, payment_id)
    
    payment_instances[job_id] = payment
    await payment.start_status_monitoring(payment_callback)
    
    # Convert simple key-value input to text
    input_text = " ".join(f"{key}: {value}" for key, value in request.items())
    
    jobs[job_id] = {
        "status": "awaiting payment",
        "payment_status": "pending",
        "payment_id": payment_id,
        "input_data": input_text
    }
    
    return {
        "job_id": job_id,
        "payment_id": payment_id
    }

async def handle_payment_status(job_id: str, payment_id: str) -> None:
    result = await execute_crew_task(jobs[job_id]["input_data"])
    print(f"Crew task completed for job {job_id}")
    
    await payment_instances[job_id].complete_payment(payment_id, result[:64])
    print(f"Payment completed for job {job_id}")
    
    output = {
        "result": result,
        "status": "completed",
        "payment_id": payment_id,
        "payment_status": "completed"
    }
    
    with open(os.path.join(RESULTS_DIR, f"{job_id}.json"), 'w') as f:
        json.dump(output, f)
    jobs[job_id]["status"] = output["status"]
    
    if job_id in payment_instances:
        payment_instances[job_id].stop_status_monitoring()
        del payment_instances[job_id]

@app.get("/status")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_id in payment_instances:
        status = await payment_instances[job_id].check_payment_status()
        jobs[job_id]["payment_status"] = status.get("data", {}).get("status")
    
    result_path = os.path.join(RESULTS_DIR, f"{job_id}.json")
    if os.path.exists(result_path):
        with open(result_path, 'r') as f:
            data = json.load(f)
            return {
                "job_id": job_id,
                "status": "completed",
                "result": data["result"]
            }
    
    return {
        "job_id": job_id,
        "status": jobs[job_id]["status"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)