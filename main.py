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
from crewai import Agent, Task, Crew
from dotenv import load_dotenv, find_dotenv
from masumi_crewai.config import Config
from masumi_crewai.payment import Payment, Amount

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

@app.on_event("startup")
async def startup_event():
    """Initialize any startup requirements"""
    pass

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up all monitoring tasks"""
    for payment in payment_instances.values():
        payment.stop_status_monitoring()

async def execute_crew_task(input_data: str) -> str:
    """
    Execute a CrewAI task with researcher and writer agents.
    
    Args:
        input_data: The research query or task description
        
    Returns:
        str: The final result from the CrewAI agents
    """
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

@app.post("/start_job")
async def start_job(request: dict):
    job_id = str(uuid.uuid4())
    agent_identifier = "dbd4d73c0910162da6bc6344ec5987175618dc42c36caa9b005ddb11a3ec9d6f"
    
    payment = Payment(
        agent_identifier=agent_identifier,
        amounts=[Amount(amount=2000000, unit="lovelace")],
        config=config
    )
    
    payment_request = await payment.create_payment_request()
    payment_id = payment_request['data']['identifier']
    
    payment.payment_ids.add(payment_id)
    
    async def payment_callback(payment_id: str):
        print(f"Callback triggered for payment {payment_id}")
        await handle_payment_status(job_id, payment_id)
    
    payment_instances[job_id] = payment
    await payment.start_status_monitoring(payment_callback)
    
    jobs[job_id] = {
        "status": "pending_payment",
        "payment_status": "pending",
        "payment_id": payment_id,
        "input_data": request["input_data"]
    }
    
    print(f"Payment tracking started for ID: {payment_id}")
    print(f"Current payment_ids in tracking: {payment.payment_ids}")
    
    return {
        "job_id": job_id,
        "payment_id": payment_id,
        "status": payment_request['status'],
        "submitResultTime": payment_request['submitResultTime']
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
    if job_id in payment_instances:
        status = await payment_instances[job_id].check_payment_status()
        jobs[job_id]["payment_status"] = status.get("data", {}).get("status")
    
    result_path = os.path.join(RESULTS_DIR, f"{job_id}.json")
    if os.path.exists(result_path):
        with open(result_path, 'r') as f:
            return json.load(f)
    
    return {
        "job_id": job_id,
        "payment_id": jobs[job_id]["payment_id"],
        "status": jobs[job_id]["status"],
        "payment_status": jobs[job_id].get("payment_status", "unknown")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)