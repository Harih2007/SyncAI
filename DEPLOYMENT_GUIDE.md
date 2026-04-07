# SyncAI Cloud Run Deployment Guide

Complete guide for deploying the multi-agent AI system to Google Cloud Run.

---

## Prerequisites

- Google Cloud account with billing enabled
- Project created in Google Cloud Console
- gcloud CLI installed

---

## Step 1: Install Google Cloud CLI

### Download and Install
Visit: https://cloud.google.com/sdk/docs/install

### Initialize
```bash
gcloud init
```

Follow prompts to:
1. Login to your Google account
2. Select or create a project
3. Set default region (recommend: us-central1)

---

## Step 2: Set Project Configuration

```bash
# Set your project ID (replace with your actual project ID)
export PROJECT_ID="your-project-id"

# Configure gcloud
gcloud config set project $PROJECT_ID

# Verify
gcloud config get-value project
```

---

## Step 3: Enable Required Google Cloud Services

```bash
# Enable Cloud Run
gcloud services enable run.googleapis.com

# Enable Cloud Build (for building containers)
gcloud services enable cloudbuild.googleapis.com

# Enable Vertex AI (for Gemini)
gcloud services enable aiplatform.googleapis.com

# Enable Firestore
gcloud services enable firestore.googleapis.com

# Verify services are enabled
gcloud services list --enabled | grep -E "run|build|aiplatform|firestore"
```

**Expected output:**
```
aiplatform.googleapis.com
cloudbuild.googleapis.com
firestore.googleapis.com
run.googleapis.com
```

---

## Step 4: Build Container with Cloud Build

From your project root directory:

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/syncai
```

**What happens:**
1. Uploads source code to Cloud Build
2. Builds Docker container using your Dockerfile
3. Pushes image to Google Container Registry
4. Takes 3-6 minutes

**Expected output:**
```
Creating temporary tarball archive...
Uploading tarball...
...
DONE
--------------------------------------------------------------------------------
ID                                    CREATE_TIME                DURATION  SOURCE
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  2024-XX-XXTXX:XX:XX+00:00  XXs       gs://...

IMAGES
gcr.io/your-project-id/syncai
```

---

## Step 5: Deploy to Cloud Run

```bash
gcloud run deploy syncai \
  --image gcr.io/$PROJECT_ID/syncai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=$PROJECT_ID,VERTEX_MODEL=gemini-2.0-flash \
  --memory 512Mi \
  --timeout 60s \
  --max-instances 10
```

**Prompts you may see:**
```
Allow unauthenticated invocations to [syncai] (y/N)?
```
Type: `y`

**Expected output:**
```
Deploying container to Cloud Run service [syncai] in project [your-project-id] region [us-central1]
✓ Deploying... Done.
  ✓ Creating Revision...
  ✓ Routing traffic...
Done.
Service [syncai] revision [syncai-00001-xxx] has been deployed and is serving 100 percent of traffic.
Service URL: https://syncai-xxxxx-uc.a.run.app
```

**Save your Service URL!**

---

## Step 6: Test the Deployed API

### Test Health Endpoint
```bash
# Replace with your actual Service URL
export SERVICE_URL="https://syncai-xxxxx-uc.a.run.app"

curl $SERVICE_URL/health
```

**Expected response:**
```json
{"status":"healthy"}
```

### Test Chat Endpoint (Full Agent Pipeline)
```bash
curl -X POST $SERVICE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Prepare my project demo meeting tomorrow"}'
```

**Expected response:**
```json
{
  "tasks": [
    "Review presentation slides",
    "Prepare demo script",
    "Rehearse presentation"
  ],
  "schedule": [
    {"task": "Review presentation slides", "time": "3PM-4PM"},
    {"task": "Rehearse presentation", "time": "6PM-7PM"}
  ],
  "notes_summary": "Recent product updates and performance metrics."
}
```

---

## Step 7: Access API Documentation

Open in browser:
```
https://syncai-xxxxx-uc.a.run.app/docs
```

You'll see:
- Interactive Swagger UI
- All endpoints documented
- Try-it-out functionality
- Request/response schemas

**Perfect for demos!**

---

## Deployment Configuration Details

### Environment Variables
- `PROJECT_ID`: Your Google Cloud project ID
- `VERTEX_MODEL`: Gemini model (gemini-2.0-flash)

### Resource Limits
- Memory: 512Mi (can increase if needed)
- Timeout: 60s (agent workflow completion time)
- Max instances: 10 (auto-scales based on traffic)

### Security
- `--allow-unauthenticated`: Public access (good for demos)
- For production: Remove this flag and add authentication

---

## Useful Commands

### View Logs
```bash
gcloud run services logs read syncai --region us-central1 --limit 50
```

### Update Environment Variables
```bash
gcloud run services update syncai \
  --region us-central1 \
  --set-env-vars VERTEX_MODEL=gemini-2.0-flash-exp
```

### Redeploy After Code Changes
```bash
# Rebuild container
gcloud builds submit --tag gcr.io/$PROJECT_ID/syncai

# Deploy new version
gcloud run deploy syncai \
  --image gcr.io/$PROJECT_ID/syncai \
  --region us-central1
```

### Delete Service
```bash
gcloud run services delete syncai --region us-central1
```

### View Service Details
```bash
gcloud run services describe syncai --region us-central1
```

---

## Troubleshooting

### Build Fails
**Error:** `requirements.txt not found`
- Ensure you're in the project root directory
- Check `requirements.txt` exists

**Error:** `Dockerfile not found`
- Ensure `Dockerfile` exists in root
- Check filename is exactly `Dockerfile` (no extension)

### Deployment Fails
**Error:** `Permission denied`
```bash
# Grant Cloud Build service account permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$(gcloud projects describe $PROJECT_ID \
  --format="value(projectNumber)")@cloudbuild.gserviceaccount.com \
  --role=roles/run.admin
```

**Error:** `Service account does not have permission`
```bash
# Enable default service account
gcloud run services update syncai \
  --region us-central1 \
  --service-account $(gcloud iam service-accounts list \
  --filter="email:*compute@developer.gserviceaccount.com" \
  --format="value(email)")
```

### API Returns Errors
**Check logs:**
```bash
gcloud run services logs read syncai --region us-central1 --limit 100
```

**Common issues:**
- Firestore not initialized: Create database in console
- Vertex AI quota: Check quotas in console
- Environment variables: Verify with `gcloud run services describe`

---

## Demo Checklist

For your hackathon presentation:

- [ ] Service URL accessible
- [ ] `/docs` page loads (Swagger UI)
- [ ] `/health` endpoint returns OK
- [ ] `/chat` endpoint returns structured response
- [ ] Response includes: tasks, schedule, notes_summary
- [ ] Logs show agent execution (optional)

---

## What You've Built

✅ **Multi-Agent AI System**
- Manager Agent (orchestration)
- Task Agent (extraction)
- Calendar Agent (scheduling)
- Info Agent (retrieval)

✅ **Production Infrastructure**
- Containerized with Docker
- Auto-scaling on Cloud Run
- Integrated with Vertex AI (Gemini)
- Persistent storage (Firestore)

✅ **API Features**
- RESTful endpoints
- Interactive documentation
- Health monitoring
- Structured responses

---

## Cost Estimate

**Cloud Run (Free Tier):**
- 2 million requests/month free
- 360,000 GB-seconds/month free

**Vertex AI (Gemini):**
- Pay per token
- ~$0.00025 per 1K input tokens
- ~$0.001 per 1K output tokens

**Firestore:**
- 1 GB storage free
- 50K reads/day free
- 20K writes/day free

**Estimated cost for demo/hackathon: < $1**

---

## Next Steps

1. **Test thoroughly** - Try different messages
2. **Prepare demo** - Practice showing the Swagger UI
3. **Monitor logs** - Watch agent execution
4. **Add features** - See enhancement suggestions below

---

## Quick Enhancement Ideas (Optional)

Want to make your project stand out? Consider adding:

1. **Streaming responses** - Real-time agent updates
2. **Conversation history** - Multi-turn dialogue
3. **Custom tools** - Email, Slack, GitHub integration
4. **Monitoring dashboard** - Agent performance metrics
5. **Rate limiting** - Production-ready API protection

Let me know if you want help implementing any of these!

---

## Support

**Documentation:**
- Cloud Run: https://cloud.google.com/run/docs
- Vertex AI: https://cloud.google.com/vertex-ai/docs
- Firestore: https://cloud.google.com/firestore/docs

**Community:**
- Stack Overflow: `google-cloud-run`, `google-vertex-ai`
- Google Cloud Community: https://www.googlecloudcommunity.com/

---

**Deployment Guide Version:** 1.0  
**Last Updated:** 2024  
**Project:** SyncAI - GenAI Meeting Preparation Assistant
