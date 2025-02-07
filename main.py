from fastapi import FastAPI, HTTPException
import uuid
import json
import os
from datetime import datetime
from typing import Dict
from crewai import Agent, Task, Crew
from dotenv import load_dotenv, find_dotenv
from masumi_crewai.config import Config
from masumi_crewai.payment import Payment, Amount

load_dotenv(find_dotenv(), override=True)

app = FastAPI()

# Storage setup
RESULTS_DIR = "job_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Track state
jobs: Dict[str, Dict[str, str]] = {}
payments: Dict[str, Payment] = {}

# Initialize config once
config = Config(
    payment_service_url=os.getenv('PAYMENT_SERVICE_URL'),
    payment_api_key=os.getenv('PAYMENT_API_KEY')
)

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
    payment_status = status.get("data", {}).get("status")
    jobs[job_id]["payment_status"] = payment_status
    
    if payment_status == "CONFIRMED":
        try:
            jobs[job_id]["status"] = "running"
            result = await execute_crew_task(jobs[job_id]["input_data"])
            
            payment = payments[job_id]
            await payment.complete_payment(result[:64])
            
            output = {
                "result": result,
                "status": "completed",
                "payment_id": jobs[job_id]["payment_id"],
                "payment_status": "completed"
            }
            
        except Exception as e:
            output = {
                "error": str(e),
                "status": "failed",
                "payment_id": jobs[job_id]["payment_id"],
                "payment_status": payment_status
            }
        
        result_path = os.path.join(RESULTS_DIR, f"{job_id}.json")
        with open(result_path, 'w') as f:
            json.dump(output, f)
        jobs[job_id]["status"] = output["status"]

@app.post("/start_job")
async def start_job(request: dict):
    if "input_data" not in request:
        raise HTTPException(status_code=400, detail="input_data is required")
        
    job_id_crew = str(uuid.uuid4())
    agent_identifier = "dbd4d73c0910162da6bc6344ec5987175618dc42c36caa9b005ddb11a3ec9d6f"
    
    try:
        payment = Payment(
            agent_identifier=agent_identifier,
            amounts=[Amount(amount=2000000, unit="lovelace")],
            config=config
        )
        
        try:
            payment_request = await payment.create_payment_request()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create payment request: {str(e)}"
            )
        
        jobs[job_id_crew] = {
            "status": "pending_payment",
            "payment_status": "pending",
            "payment_id": payment_request['data']['identifier'],
            "input_data": request["input_data"]
        }
        payments[job_id_crew] = payment
        
        return {
            "job_id": job_id_crew,
            "payment_id": payment_request['data']['identifier'],
            "status": payment_request['status'],
            "submitResultTime": payment_request['submitResultTime']
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.get("/status")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_id in payments:
        status = await payments[job_id].check_payment_status()
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