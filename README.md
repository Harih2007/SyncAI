# GenAI Meeting Preparation Assistant

A production-ready multi-agent AI backend for automated meeting preparation, built with **FastAPI**, **Google Agent Development Kit (ADK)**, and **Gemini via Vertex AI**. Designed for deployment on **Google Cloud Run**.

## Architecture

```
┌─────────────────────────────────────────────────┐
│               FastAPI Server                    │
│                 POST /chat                      │
├─────────────────────────────────────────────────┤
│              Manager Agent                      │
│   ┌───────────┬──────────────┬──────────────┐   │
│   │  Task     │  Calendar    │    Info       │   │
│   │  Agent    │  Agent       │    Agent      │   │
│   └───────────┴──────────────┴──────────────┘   │
│        │            │              │            │
│   Gemini via    Calendar       Firestore        │
│   Vertex AI     Tool           Client           │
└─────────────────────────────────────────────────┘
```

### Agents

| Agent | Role |
|-------|------|
| **Manager Agent** | Orchestrates all sub-agents sequentially and merges their outputs |
| **Task Agent** | Extracts actionable preparation tasks from the user request |
| **Calendar Agent** | Creates suggested preparation time blocks for each task |
| **Info Agent** | Retrieves relevant notes from Firestore for the meeting topic |

### Workflow

1. User sends a meeting preparation request to `POST /chat`
2. **Manager Agent** analyzes the request and orchestrates:
   - → **Task Agent** extracts preparation tasks
   - → **Calendar Agent** schedules preparation time blocks
   - → **Info Agent** retrieves relevant notes from Firestore
3. Manager Agent merges all outputs
4. API returns a structured meeting preparation plan

## Project Structure

```
genai-meeting-assistant/
├── main.py                    # FastAPI entry point
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Cloud Run container definition
├── .env.example               # Environment variable template
├── .dockerignore              # Docker build exclusions
├── README.md                  # This file
│
├── agents/                    # Multi-agent architecture
│   ├── __init__.py
│   ├── manager_agent.py       # Orchestrator agent
│   ├── task_agent.py          # Task extraction agent
│   ├── calendar_agent.py      # Schedule planning agent
│   └── info_agent.py          # Information retrieval agent
│
├── tools/                     # Agent tool functions
│   ├── __init__.py
│   └── calendar_tool.py       # Time block scheduling utilities
│
├── database/                  # Firestore data access
│   ├── __init__.py
│   └── firestore_client.py    # Firestore client & helpers
│
└── api/                       # FastAPI routes & models
    ├── __init__.py
    └── routes.py              # Endpoint definitions
```

## Prerequisites

- **Python 3.10+**
- **Google Cloud Project** with the following APIs enabled:
  - Vertex AI API
  - Cloud Firestore API
  - Cloud Run API (for deployment)
- **Google Cloud CLI** (`gcloud`) installed and authenticated
- **Service Account** with roles:
  - `roles/aiplatform.user` (Vertex AI)
  - `roles/datastore.user` (Firestore)

## Local Development

### 1. Clone and Install Dependencies

```bash
cd genai-meeting-assistant
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Set Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
VERTEX_MODEL=gemini-2.0-flash
```

> **Note:** On Cloud Run, `GOOGLE_APPLICATION_CREDENTIALS` is not needed — Application Default Credentials (ADC) are automatically available via the metadata server.

### 3. Run the Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

Or with auto-reload for development:

```bash
python main.py
```

The API will be available at:
- **API:** http://localhost:8080
- **Swagger UI:** http://localhost:8080/docs
- **ReDoc:** http://localhost:8080/redoc

### 4. Test the API

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Prepare my project demo meeting tomorrow"}'
```

Expected response:

```json
{
  "tasks": [
    "Review and update presentation slides with latest metrics",
    "Rehearse demo flow including backup scenarios",
    "Test all demo environments and verify connectivity",
    "Prepare answers for anticipated stakeholder questions",
    "Gather latest performance metrics and KPI data"
  ],
  "schedule": [
    {"task": "Review and update presentation slides", "time": "9:00 AM - 10:00 AM"},
    {"task": "Rehearse demo flow", "time": "10:15 AM - 11:00 AM"},
    {"task": "Test demo environments", "time": "11:15 AM - 12:15 PM"},
    {"task": "Prepare Q&A responses", "time": "1:00 PM - 2:00 PM"},
    {"task": "Gather metrics", "time": "2:15 PM - 2:45 PM"}
  ],
  "notes_summary": "Key product metrics: DAU increased 15% MoM. API latency reduced to 120ms p99. Customer satisfaction score at 4.6/5.",
  "processing_time_seconds": 4.2
}
```

## Deployment to Google Cloud Run

### 1. Authenticate with Google Cloud

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  cloudbuild.googleapis.com
```

### 3. Build the Container

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/meeting-agent
```

### 4. Deploy to Cloud Run

```bash
gcloud run deploy meeting-agent \
  --image gcr.io/PROJECT_ID/meeting-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "PROJECT_ID=YOUR_PROJECT_ID,VERTEX_MODEL=gemini-2.0-flash" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10
```

### 5. Verify Deployment

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe meeting-agent \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)')

# Health check
curl $SERVICE_URL/health

# Test the API
curl -X POST $SERVICE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Prepare my project demo meeting tomorrow"}'
```

## API Reference

### `POST /chat`

Submit a meeting preparation request.

**Request Body:**
```json
{
  "message": "Prepare my project demo meeting tomorrow"
}
```

**Response (200 OK):**
```json
{
  "tasks": ["string"],
  "schedule": [{"task": "string", "time": "string"}],
  "notes_summary": "string",
  "processing_time_seconds": 0.0
}
```

### `GET /health`

Health check for Cloud Run and load balancers.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "meeting-preparation-assistant",
  "version": "1.0.0"
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PROJECT_ID` | Yes | — | Google Cloud project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | Local only | ADC | Path to service account JSON key |
| `VERTEX_MODEL` | No | `gemini-2.0-flash` | Gemini model identifier |
| `PORT` | No | `8080` | Server port (set by Cloud Run) |

## Firestore Collections

| Collection | Purpose |
|------------|---------|
| `meeting_tasks` | Stores extracted preparation tasks per session |
| `meeting_notes` | Stores notes and information (searchable by tags) |
| `meeting_results` | Stores complete meeting preparation results |

## License

MIT License — see [LICENSE](LICENSE) for details.
