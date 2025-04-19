import os
import uvicorn
import uuid
import asyncio
import json
import httpx
import time
from queue import Queue
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel, Field, field_validator
from masumi.config import Config
from masumi.payment import Payment, Amount
from crew_definition import ResearchCrew
from logging_config import setup_logging, get_log_buffer

# Configure logging
logger = setup_logging()

# Load environment variables
load_dotenv(override=True)

# Retrieve API Keys and URLs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL")
PAYMENT_API_KEY = os.getenv("PAYMENT_API_KEY")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "iofsnaiojdoiewqajdriknjonasfoinasd")  # Default token if not set

logger.info("Starting application with configuration:")
logger.info(f"PAYMENT_SERVICE_URL: {PAYMENT_SERVICE_URL}")

# Initialize FastAPI
app = FastAPI(
    title="API following the Masumi API Standard",
    description="API for running Agentic Services tasks with Masumi payment integration",
    version="1.0.0"
)

# ─────────────────────────────────────────────────────────────────────────────
# Temporary in-memory job store (DO NOT USE IN PRODUCTION)
# ─────────────────────────────────────────────────────────────────────────────
jobs = {}
payment_instances = {}
super_jobs = {}  # For tracking startSuper jobs

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
    identifier_from_purchaser: str
    input_data: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "identifier_from_purchaser": "example_purchaser_123",
                "input_data": {
                    "text": "Write a story about a robot learning to paint"
                }
            }
        }

class ProvideInputRequest(BaseModel):
    job_id: str

# ─────────────────────────────────────────────────────────────────────────────
# SuperJob Execution Model
# ─────────────────────────────────────────────────────────────────────────────
class StartSuperRequest(BaseModel):
    identifier: str = "123123123123123"
    address: str = "addr1...."
    
    class Config:
        json_schema_extra = {
            "example": {
                "identifier": "unique_purchaser_id",
                "address": "addr1q9fjd9ca0mz8va2r8755rsg8f0wrpxrplxmuywx4ky4stgxyq9zqacteq5u0d9j46alzkc4pp79m8sxeejhfu8r0lmeqcfvlfl"
            }
        }

# ─────────────────────────────────────────────────────────────────────────────
# CrewAI Task Execution
# ─────────────────────────────────────────────────────────────────────────────
async def execute_crew_task(input_data: str) -> str:
    """ Execute a CrewAI task with Research and Writing Agents """
    logger.info(f"Starting CrewAI task with input: {input_data}")
    crew = ResearchCrew(logger=logger, wallet_balance=input_data)
    result = crew.crew.kickoff()
    logger.info("CrewAI task completed successfully")
    return result

# ─────────────────────────────────────────────────────────────────────────────
# 1) Start Job (MIP-003: /start_job)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/start_job")
async def start_job(data: StartJobRequest):
    """ Initiates a job and creates a payment request """
    print(f"Received data: {data}")
    print(f"Received data.input_data: {data.input_data}")
    try:
        job_id = str(uuid.uuid4())
        agent_identifier = os.getenv("AGENT_IDENTIFIER")
        
        # Log the input text (truncate if too long)
        input_text = data.input_data
        truncated_input = input_text[:100] + "..." if len(input_text) > 100 else input_text
        logger.info(f"Received job request with input: '{truncated_input}'")
        logger.info(f"Starting job {job_id} with agent {agent_identifier}")

        # Define payment amounts
        payment_amount = os.getenv("PAYMENT_AMOUNT", "10000000")  # Default 10 ADA
        payment_unit = os.getenv("PAYMENT_UNIT", "lovelace") # Default lovelace

        amounts = [Amount(amount=payment_amount, unit=payment_unit)]
        logger.info(f"Using payment amount: {payment_amount} {payment_unit}")
        
        # Create a payment request using Masumi
        payment = Payment(
            agent_identifier=agent_identifier,
            #amounts=amounts,
            config=config,
            identifier_from_purchaser=data.identifier_from_purchaser,
            input_data={"wallet_balance": data.input_data}
        )
        
        logger.info("Creating payment request...")
        payment_request = await payment.create_payment_request()
        payment_id = payment_request["data"]["blockchainIdentifier"]
        payment.payment_ids.add(payment_id)
        logger.info(f"Created payment request with ID: {payment_id}")

        # Store job info (Awaiting payment)
        jobs[job_id] = {
            "status": "awaiting_payment",
            "payment_status": "pending",
            "payment_id": payment_id,
            "input_data": data.input_data,
            "result": None,
            "identifier_from_purchaser": data.identifier_from_purchaser
        }

        async def payment_callback(payment_id: str):
            await handle_payment_status(job_id, payment_id)

        # Start monitoring the payment status
        payment_instances[job_id] = payment
        logger.info(f"Starting payment status monitoring for job {job_id}")
        await payment.start_status_monitoring(payment_callback)

        # Return the response in the required format
        return {
            "status": "success",
            "job_id": job_id,
            "blockchainIdentifier": payment_request["data"]["blockchainIdentifier"],
            "submitResultTime": payment_request["data"]["submitResultTime"],
            "unlockTime": payment_request["data"]["unlockTime"],
            "externalDisputeUnlockTime": payment_request["data"]["externalDisputeUnlockTime"],
            "agentIdentifier": agent_identifier,
            "sellerVkey": os.getenv("SELLER_VKEY"),
            "identifierFromPurchaser": data.identifier_from_purchaser,
            "amounts": amounts,
            "input_hash": payment.input_hash
        }
    except KeyError as e:
        logger.error(f"Missing required field in request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Bad Request: If input_data or identifier_from_purchaser is missing, invalid, or does not adhere to the schema."
        )
    except Exception as e:
        logger.error(f"Error in start_job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Input_data or identifier_from_purchaser is missing, invalid, or does not adhere to the schema."
        )

# ─────────────────────────────────────────────────────────────────────────────
# 2) Process Payment and Execute AI Task
# ─────────────────────────────────────────────────────────────────────────────
async def handle_payment_status(job_id: str, payment_id: str) -> None:
    """ Executes CrewAI task after payment confirmation """
    try:
        logger.info(f"Payment {payment_id} completed for job {job_id}, executing task...")
        
        # Update job status to running
        jobs[job_id]["status"] = "running"
        logger.info(f"Input data: {jobs[job_id]["input_data"]}")

        # Execute the AI task
        result = await execute_crew_task(jobs[job_id]["input_data"])
        result_dict = result.json_dict
        logger.info(f"Crew task completed for job {job_id}")
        
        # Mark payment as completed on Masumi
        # Use a shorter string for the result hash
        await payment_instances[job_id].complete_payment(payment_id, result_dict)
        logger.info(f"Payment completed for job {job_id}")

        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["payment_status"] = "completed"
        jobs[job_id]["result"] = result

        # Stop monitoring payment status
        if job_id in payment_instances:
            payment_instances[job_id].stop_status_monitoring()
            del payment_instances[job_id]
    except Exception as e:
        logger.error(f"Error processing payment {payment_id} for job {job_id}: {str(e)}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        
        # Still stop monitoring to prevent repeated failures
        if job_id in payment_instances:
            payment_instances[job_id].stop_status_monitoring()
            del payment_instances[job_id]

# ─────────────────────────────────────────────────────────────────────────────
# 3) Check Job and Payment Status (MIP-003: /status)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/status")
async def get_status(job_id: str):
    """ Retrieves the current status of a specific job """
    logger.info(f"Checking status for job {job_id}")
    if job_id not in jobs:
        logger.warning(f"Job {job_id} not found")
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Check latest payment status if payment instance exists
    if job_id in payment_instances:
        try:
            status = await payment_instances[job_id].check_payment_status()
            job["payment_status"] = status.get("data", {}).get("status")
            logger.info(f"Updated payment status for job {job_id}: {job['payment_status']}")
        except ValueError as e:
            logger.warning(f"Error checking payment status: {str(e)}")
            job["payment_status"] = "unknown"
        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}", exc_info=True)
            job["payment_status"] = "error"

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
        "agentIdentifier": os.getenv("AGENT_IDENTIFIER"),
        "message": "The server is running smoothly."
    }

# ─────────────────────────────────────────────────────────────────────────────
# 5) Retrieve Input Schema (MIP-003: /input_schema)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/input_schema")
async def input_schema():
    """
    Returns the expected input schema for the /start_job endpoint.
    Fulfills MIP-003 /input_schema endpoint.
    """
    return {
        "input_data": [
            {
                "id": "text",
                "type": "string",
                "name": "Task Description",
                "data": {
                    "description": "The text input for the AI task",
                    "placeholder": "Enter your task description here"
                }
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 6) Health Check
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """
    Returns the health of the server.
    """
    return {
        "status": "healthy"
    }

# ─────────────────────────────────────────────────────────────────────────────
# Log Streaming Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/logs")
async def stream_logs():
    """Stream logs in real-time as server-sent events"""
    
    # Function to generate the SSE stream
    async def event_generator():
        # Create a queue for this client
        my_queue = Queue()
        
        # Register the queue as a listener
        log_buffer = get_log_buffer()
        log_buffer.add_listener(my_queue)
        
        # Send the recent logs first
        recent_logs = log_buffer.get_recent_logs(100)
        for log in recent_logs:
            yield f"data: {json.dumps(log)}\n\n"
        
        try:
            # Keep the connection open and stream new logs
            while True:
                # Non-blocking check for new logs
                try:
                    # Use a small timeout to avoid blocking too long
                    log_entry = await asyncio.to_thread(my_queue.get, timeout=0.1)
                    yield f"data: {json.dumps(log_entry)}\n\n"
                except:
                    # No new logs, send a heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
                
                # Give other tasks a chance to run
                await asyncio.sleep(0.1)
        finally:
            # Make sure to remove the listener when client disconnects
            log_buffer.remove_listener(my_queue)
    
    # Set up the streaming response
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for Nginx
        }
    )

# ─────────────────────────────────────────────────────────────────────────────
# HTML Log Viewer Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/log-viewer")
async def log_viewer():
    """Provide a simple HTML page to view logs in real-time"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Real-time Logs</title>
        <style>
            body {
                font-family: monospace;
                background-color: #1e1e1e;
                color: #d4d4d4;
                margin: 0;
                padding: 20px;
            }
            #log-container {
                height: calc(100vh - 140px);
                overflow-y: auto;
                border: 1px solid #333;
                padding: 10px;
                background-color: #252526;
                border-radius: 4px;
            }
            .log-entry {
                margin-bottom: 5px;
                padding: 5px;
                border-radius: 3px;
            }
            .log-INFO {
                color: #569cd6;
            }
            .log-WARNING {
                color: #dcdcaa;
            }
            .log-ERROR {
                color: #f44747;
            }
            .log-DEBUG {
                color: #6a9955;
            }
            .log-CRITICAL {
                color: #f44747;
                font-weight: bold;
                background-color: #3a0000;
            }
            .header {
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                align-items: center;
            }
            button {
                background-color: #0e639c;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                cursor: pointer;
                margin-left: 10px;
            }
            button:hover {
                background-color: #1177bb;
            }
            .filter-controls {
                margin-bottom: 10px;
                padding: 10px;
                background-color: #252526;
                border-radius: 4px;
            }
            .filter-controls label {
                margin-right: 15px;
            }
            #search-box {
                padding: 5px;
                border-radius: 3px;
                border: 1px solid #555;
                background-color: #333;
                color: #d4d4d4;
                width: 250px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Real-time Logs</h1>
            <div>
                <button id="btn-clear">Clear</button>
                <button id="btn-pause">Pause</button>
            </div>
        </div>
        
        <div class="filter-controls">
            <label><input type="checkbox" class="level-filter" value="INFO" checked> INFO</label>
            <label><input type="checkbox" class="level-filter" value="WARNING" checked> WARNING</label>
            <label><input type="checkbox" class="level-filter" value="ERROR" checked> ERROR</label>
            <label><input type="checkbox" class="level-filter" value="DEBUG" checked> DEBUG</label>
            <label><input type="checkbox" class="level-filter" value="CRITICAL" checked> CRITICAL</label>
            <input type="text" id="search-box" placeholder="Search logs...">
        </div>
        
        <div id="log-container"></div>
        
        <script>
            let isPaused = false;
            let eventSource;
            const logContainer = document.getElementById('log-container');
            const btnPause = document.getElementById('btn-pause');
            const btnClear = document.getElementById('btn-clear');
            const searchBox = document.getElementById('search-box');
            const levelFilters = document.querySelectorAll('.level-filter');
            
            function formatTimestamp(timestamp) {
                const date = new Date(timestamp * 1000);
                return date.toISOString().replace('T', ' ').substr(0, 23);
            }
            
            function connectToEventSource() {
                if (eventSource) {
                    eventSource.close();
                }
                
                eventSource = new EventSource('/logs');
                
                eventSource.onmessage = function(event) {
                    if (isPaused) return;
                    
                    const data = JSON.parse(event.data);
                    
                    // Skip heartbeats
                    if (data.type === 'heartbeat') return;
                    
                    // Check if we should display this log based on level filters
                    const levelCheckbox = document.querySelector(`.level-filter[value="${data.level}"]`);
                    if (levelCheckbox && !levelCheckbox.checked) return;
                    
                    // Check if log matches search
                    const searchTerm = searchBox.value.toLowerCase();
                    if (searchTerm && !data.message.toLowerCase().includes(searchTerm)) return;
                    
                    const entry = document.createElement('div');
                    entry.className = `log-entry log-${data.level}`;
                    
                    // Format: [timestamp] [level] [logger] message
                    entry.textContent = `[${formatTimestamp(data.timestamp)}] [${data.level}] [${data.logger}] ${data.message}`;
                    
                    logContainer.appendChild(entry);
                    logContainer.scrollTop = logContainer.scrollHeight;
                };
                
                eventSource.onerror = function() {
                    console.error('EventSource failed. Reconnecting in 5 seconds...');
                    setTimeout(connectToEventSource, 5000);
                };
            }
            
            // Initial connection
            connectToEventSource();
            
            // Setup UI interactions
            btnPause.addEventListener('click', function() {
                isPaused = !isPaused;
                btnPause.textContent = isPaused ? 'Resume' : 'Pause';
            });
            
            btnClear.addEventListener('click', function() {
                logContainer.innerHTML = '';
            });
            
            // Filter logs when search box changes
            searchBox.addEventListener('input', function() {
                const searchTerm = this.value.toLowerCase();
                const entries = logContainer.querySelectorAll('.log-entry');
                
                entries.forEach(entry => {
                    const text = entry.textContent.toLowerCase();
                    if (searchTerm === '' || text.includes(searchTerm)) {
                        entry.style.display = '';
                    } else {
                        entry.style.display = 'none';
                    }
                });
            });
            
            // Filter by log level
            levelFilters.forEach(checkbox => {
                checkbox.addEventListener('change', function() {
                    const level = this.value;
                    const entries = logContainer.querySelectorAll(`.log-${level}`);
                    
                    entries.forEach(entry => {
                        entry.style.display = this.checked ? '' : 'none';
                    });
                });
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)

# ─────────────────────────────────────────────────────────────────────────────
# startSuper Endpoint - One-Click Process
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/startSuper")
async def start_super(data: StartSuperRequest, background_tasks: BackgroundTasks):
    """
    All-in-one endpoint that handles job creation, payment, and execution
    """

    # todo use the data.address to fetch wallet balance
    wallet_balance = "100 ADA, 9000 NMKR"

    taskInfo = f"User portofolio consists of: {wallet_balance}" 
    job_id = str(uuid.uuid4())
    logger.info(f"Starting super job {job_id} with identifier {data.identifier}")
    
    # Track job in super_jobs
    super_jobs[job_id] = {
        "status": "initializing",
        "identifier": data.identifier,
        "text": taskInfo,
        "start_time": time.time(),
        "payment_status": "pending",
        "result": None
    }
    
    # Launch the process in the background
    background_tasks.add_task(
        process_super_job, 
        job_id=job_id, 
        identifier=data.identifier, 
        taskInfo=taskInfo,
        payment_token=PAYMENT_TOKEN
    )
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": "Super job started. Check /superStatus?job_id={job_id} for updates."
    }

# ─────────────────────────────────────────────────────────────────────────────
# superStatus Endpoint - Check Super Job Status
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/superStatus")
async def super_status(job_id: str):
    """Check the status of a super job"""
    if job_id not in super_jobs:
        raise HTTPException(status_code=404, detail="Super job not found")
    
    job = super_jobs[job_id]
    
    # Calculate elapsed time
    elapsed = time.time() - job["start_time"]
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "payment_status": job["payment_status"],
        "elapsed_seconds": round(elapsed, 1),
        "result": job.get("result")
    }

# ─────────────────────────────────────────────────────────────────────────────
# Super Job Processing
# ─────────────────────────────────────────────────────────────────────────────
async def process_super_job(job_id: str, identifier: str, taskInfo: str, payment_token: str):
    """
    Process a super job from start to finish, similar to call_api.sh
    """
    try:
        # Step 1: Call start_job endpoint
        super_jobs[job_id]["status"] = "starting_job"
        logger.info(f"Starting job for super job {job_id}")
        
        start_job_data = {
            "identifier_from_purchaser": identifier,
            "input_data": taskInfo,
        }
        
        # Make internal call to start_job using httpx
        async with httpx.AsyncClient() as client:
            start_job_response = await client.post(
                f"http://localhost:{os.getenv('PORT', '8000')}/start_job",
                json=start_job_data,
                timeout=30.0
            )
            
        if start_job_response.status_code != 200:
            raise Exception(f"Failed to start job: {start_job_response.text}")
            
        start_job_data = start_job_response.json()
        logger.info(f"Job started successfully: {start_job_data['job_id']}")
        
        # Save relevant data
        job_info = {
            "internal_job_id": start_job_data["job_id"],
            "blockchain_id": start_job_data["blockchainIdentifier"],
            "submit_time": start_job_data["submitResultTime"],
            "unlock_time": start_job_data["unlockTime"],
            "dispute_time": start_job_data["externalDisputeUnlockTime"],
            "agent_id": start_job_data["agentIdentifier"],
            "seller_vkey": start_job_data["sellerVkey"],
            "input_hash": start_job_data["input_hash"],
            "amounts": start_job_data["amounts"]
        }
        
        super_jobs[job_id].update(job_info)
        super_jobs[job_id]["status"] = "processing_payment"
        
        # Step 2: Call payment API
        logger.info(f"Processing payment for super job {job_id}")
        
        payment_data = {
            "status": "success",
            "network": "Preprod",
            "paymentType": "Web3CardanoV1",
            "job_id": job_info["internal_job_id"],
            "blockchainIdentifier": job_info["blockchain_id"],
            "submitResultTime": job_info["submit_time"],
            "unlockTime": job_info["unlock_time"],
            "externalDisputeUnlockTime": job_info["dispute_time"],
            "agentIdentifier": job_info["agent_id"],
            "sellerVkey": job_info["seller_vkey"],
            "identifierFromPurchaser": identifier,
            "amounts": job_info["amounts"],
            "inputHash": job_info["input_hash"]
        }
        
        # Call payment API
        async with httpx.AsyncClient() as client:
            payment_response = await client.post(
                "https://payment.masumi.network/api/v1/purchase/",
                json=payment_data,
                headers={
                    "token": payment_token,
                    "Content-Type": "application/json",
                    "accept": "application/json"
                },
                timeout=30.0
            )
            
        if payment_response.status_code != 200:
            logger.error(f"Payment API error: {payment_response.text}")
            super_jobs[job_id]["payment_status"] = "failed"
            super_jobs[job_id]["status"] = "payment_error"
            super_jobs[job_id]["error"] = f"Payment API error: {payment_response.text}"
            return
            
        logger.info(f"Payment completed for super job {job_id}")
        super_jobs[job_id]["payment_status"] = "completed"
        super_jobs[job_id]["status"] = "waiting_for_processing"
        
        # Step 3: Wait for processing (similar to countdown in call_api.sh)
        logger.info(f"Waiting for job to complete for super job {job_id}")
        
        # Wait for up to 10 minutes (600 seconds), checking status every 10 seconds
        max_wait_time = 600  # 10 minutes
        check_interval = 10   # 10 seconds
        
        for i in range(0, max_wait_time, check_interval):
            # Check job status
            async with httpx.AsyncClient() as client:
                status_response = await client.get(
                    f"http://localhost:{os.getenv('PORT', '8000')}/status?job_id={job_info['internal_job_id']}",
                    timeout=10.0
                )
                
            if status_response.status_code != 200:
                logger.warning(f"Status check failed: {status_response.text}")
                await asyncio.sleep(check_interval)
                continue
                
            status_data = status_response.json()
            super_jobs[job_id]["status"] = status_data["status"]
            
            # If job is completed, get the result and break
            if status_data["status"] == "completed":
                super_jobs[job_id]["result"] = status_data["result"]
                logger.info(f"Job completed for super job {job_id}")
                break
                
            # If job failed, break
            if status_data["status"] == "failed":
                super_jobs[job_id]["error"] = "Job failed"
                logger.error(f"Job failed for super job {job_id}")
                break
                
            # Wait before the next check
            await asyncio.sleep(check_interval)
                
        # If we've waited the maximum time and job isn't complete
        if super_jobs[job_id]["status"] not in ["completed", "failed"]:
            super_jobs[job_id]["status"] = "timed_out"
            logger.warning(f"Job timed out for super job {job_id}")
            
    except Exception as e:
        logger.error(f"Error processing super job {job_id}: {str(e)}", exc_info=True)
        super_jobs[job_id]["status"] = "error"
        super_jobs[job_id]["error"] = str(e)

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
