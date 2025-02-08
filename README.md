# Masumi CrewAI Reference Implementation

This repository provides a **FastAPI** service that integrates **CrewAI** with the **Masumi payment system**. It enables users to submit AI-driven tasks that require payment, process transactions through Masumi, and execute the requested AI tasks once the payment is confirmed.

## Features

- **AI Task Execution with Payment Verification**: Users can submit AI-based tasks that are only processed once the payment is confirmed.
- **Integration with Masumi Payments**: Handles payments using the Masumi payment system, including creating payment requests, monitoring transactions, and confirming payments.
- **Automated CrewAI Workflow**: Uses **CrewAI** agents to perform research and content summarization tasks dynamically.
- **Job and Payment Status Tracking**: Provides API endpoints to check the status of both AI jobs and payments.
- **Asynchronous Execution**: Ensures smooth handling of payment confirmations and job processing.

## Tech Stack

- **FastAPI** - Web framework for API development.
- **CrewAI** - AI agent framework for executing research and summarization tasks.
- **Masumi Payment System** - Secure and decentralized payment processing.
- **Python 3.9+** - Programming language for backend services.

---

## Getting Started

### Prerequisites

- Python **3.9+**
- [Poetry](https://python-poetry.org/docs/) (Recommended) or `pip`
- FastAPI & Uvicorn
- CrewAI & dotenv
- A valid Masumi payment service account with API credentials.

### Installation

#### 1. Clone the repository

```sh
git clone https://github.com/masumi-network/masumi-crewai-reference-implementation.git
cd masumi-crewai-reference-implementation
```

#### 2. Install dependencies

Using **Poetry**:

```sh
poetry install
```

Using **pip**:

```sh
pip install -r requirements.txt
```

#### 3. Set up environment variables

Copy the example environment file:

```sh
cp .env.example .env
```

Edit `.env` and configure your Masumi payment system credentials:

```ini
PAYMENT_SERVICE_URL=<Masumi Payment API URL>
PAYMENT_API_KEY=<Your Masumi API Key>
```

---

## Usage

### Running the API Server

```sh
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be accessible at `http://localhost:8000`.

---

## API Endpoints

### 1. Start a new AI task and payment request

**Endpoint:**
```http
POST /start_job
```

**Request Body:**
```json
{
  "input_data": "Research about AI governance models"
}
```

**Response:**
```json
{
  "job_id": "1234-5678-uuid",
  "payment_id": "abcd-efgh-5678",
  "status": "pending_payment",
  "submitResultTime": "2025-02-10T12:00:00Z"
}
```

---

### 2. Check job and payment status

**Endpoint:**
```http
GET /status?job_id=<job_id>
```

**Response (Pending Payment):**
```json
{
  "job_id": "1234-5678-uuid",
  "payment_id": "abcd-efgh-5678",
  "status": "pending_payment",
  "payment_status": "pending"
}
```

**Response (Completed Task):**
```json
{
  "job_id": "1234-5678-uuid",
  "payment_id": "abcd-efgh-5678",
  "status": "completed",
  "payment_status": "completed",
  "result": "AI-generated summary of research..."
}
```

---

## Project Structure

```
masumi-crewai-reference-implementation/
│── masumi_crewai/            # Core logic for CrewAI integration
│   ├── config.py             # Configuration management
│   ├── payment.py            # Payment handling logic
│── job_results/              # Storage for completed job results
│── main.py                   # FastAPI server with endpoints
│── .env.example              # Example environment variables
│── requirements.txt          # Dependencies (if not using Poetry)
│── README.md                 # Documentation
```

---

## How It Works

1. A user submits an AI research task using `/start_job`, which triggers:
   - Creation of a **Masumi payment request**.
   - Job tracking with a **unique job ID**.
   - Asynchronous monitoring of the payment status.

2. Once the payment is confirmed:
   - A **CrewAI agent** executes the research and summarization task.
   - The **final AI-generated output** is stored and returned.
   - Payment is marked as **completed**.

3. Users can check the status of their job and payment at any time via `/status`.

---

## Contributing

We welcome contributions! Follow these steps:

1. Fork the repository.
2. Create a new branch:
   ```sh
   git checkout -b feature/your-feature
   ```
3. Make changes and commit:
   ```sh
   git commit -m "Add new feature"
   ```
4. Push to your branch:
   ```sh
   git push origin feature/your-feature
   ```
5. Open a pull request.

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Contact

For support or inquiries, please reach out to **Masumi Network** at:

- **Website**: [masumi.network](https://masumi.network)
- **Twitter**: [@Masumi_Network](https://twitter.com/Masumi_Network)
