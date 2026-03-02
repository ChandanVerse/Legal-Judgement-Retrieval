# AWS EC2 Deployment Guide

Deploy the Legal Case Search system to AWS EC2 with DynamoDB + S3 storage.

## Architecture

```
LOCAL (Your PC - RTX 4060)              AWS Cloud
┌─────────────────────┐                ┌─────────────────────────────┐
│ ingest.py           │                │  EC2 (t2.micro)             │
│ embedder.py (GPU)   │                │  ├── api_server.py          │
│ run_ingest.py       │                │  ├── search.py              │
└─────────┬───────────┘                │  └── frontend (Next.js)     │
          │                            └──────────┬──────────────────┘
          │                                       │
          └───────────────┬───────────────────────┘
                          ▼
         ┌────────────────────────────────────────┐
         │           AWS Services                 │
         │  ┌──────────────┐  ┌───────────────┐  │
         │  │  DynamoDB    │  │  S3 Bucket    │  │
         │  │  (case text) │  │  (PDFs)       │  │
         │  └──────────────┘  └───────────────┘  │
         └────────────────────────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         │       External Services         │
         │  - Pinecone (vectors)           │
         │  - Google Gemini API            │
         └─────────────────────────────────┘
```

## Prerequisites

1. **AWS Account** with free tier
2. **Created AWS Resources:**
   - IAM user with DynamoDB + S3 access
   - DynamoDB table: `legal-cases` (partition key: `case_id`)
   - S3 bucket: `legal-case-pdfs-YOUR_UNIQUE_ID`
3. **EC2 Instance:** Ubuntu 22.04, t2.micro (free tier)

## AWS Setup (Before EC2)

### Step 1: Create IAM User
1. AWS Console → IAM → Users → Create User
2. Name: `legal-case-api`
3. Attach policies:
   - `AmazonDynamoDBFullAccess`
   - `AmazonS3FullAccess`
4. Create access key → **Download credentials**

### Step 2: Create DynamoDB Table
1. AWS Console → DynamoDB → Create Table
2. Table name: `legal-cases`
3. Partition key: `case_id` (String)
4. Settings: Default (on-demand capacity)
5. Create table

### Step 3: Create S3 Bucket
1. AWS Console → S3 → Create Bucket
2. Bucket name: `legal-case-pdfs-YOUR_UNIQUE_ID` (globally unique)
3. Region: Same as DynamoDB (e.g., `ap-south-1`)
4. Block public access: Keep enabled
5. Create bucket

### Step 4: Migrate Data (Run Locally)

Before deploying, migrate your data from MongoDB to AWS:

```bash
# Add AWS credentials to your local .env
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
DYNAMODB_TABLE=legal-cases
S3_BUCKET=legal-case-pdfs-your-unique-id

# Run migration
python deploy/scripts/migrate-to-aws.py
```

## EC2 Deployment

### Step 1: Launch EC2 Instance

1. AWS Console → EC2 → Launch Instance
2. **Name:** `legal-case-search`
3. **AMI:** Ubuntu Server 22.04 LTS (free tier)
4. **Instance type:** t2.micro (free tier)
5. **Key pair:** Create new → Download `.pem` file
6. **Security Group rules:**
   - SSH (22) - My IP
   - Custom TCP 3000 - Anywhere (0.0.0.0/0)
   - Custom TCP 8000 - Anywhere (0.0.0.0/0)
7. **Storage:** 20 GB gp3
8. Launch instance

### Step 2: Connect to EC2

From Windows PowerShell:
```powershell
ssh -i "your-key.pem" ubuntu@YOUR_EC2_PUBLIC_IP
```

### Step 3: Initial Setup

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/Legal-Judgement-Retrieval.git
cd Legal-Judgement-Retrieval

# Create .env from template
cp deploy/.env.example .env
nano .env  # Add your API keys (Ctrl+X, Y, Enter to save)

# Run setup script
chmod +x deploy/scripts/*.sh
./deploy/scripts/setup-ec2.sh
```

### Step 4: Deploy

```bash
./deploy/scripts/deploy.sh
```

### Step 5: Configure Frontend URL

```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=http://YOUR_EC2_IP:8000" > .env.production.local
npm run build
sudo systemctl restart legal-frontend
```

## Verification

1. **Test API:**
   ```bash
   curl http://localhost:8000/health
   # {"status":"ok"}

   curl http://localhost:8000/api/cases
   # {"cases": [...], "total": N}
   ```

2. **Test from browser:**
   - Frontend: `http://YOUR_EC2_IP:3000`
   - API: `http://YOUR_EC2_IP:8000/health`

3. **Full flow test:**
   - Open frontend in browser
   - Type "find cases about cheque bounce"
   - Verify search results appear

## Useful Commands

```bash
# Check service status
sudo systemctl status legal-api
sudo systemctl status legal-frontend

# View logs
sudo journalctl -u legal-api -f
sudo journalctl -u legal-frontend -f

# Restart services
sudo systemctl restart legal-api legal-frontend

# Stop services
sudo systemctl stop legal-api legal-frontend
```

## Updating the Application

```bash
cd /home/ubuntu/Legal-Judgement-Retrieval
git pull

# If Python dependencies changed:
source .venv/bin/activate
pip install -r deploy/requirements-server.txt
sudo systemctl restart legal-api

# If frontend changed:
cd frontend
npm install
npm run build
sudo systemctl restart legal-frontend
```

## Cost Summary

| Resource | Free Tier | After Free Tier |
|----------|-----------|-----------------|
| EC2 t2.micro | 750 hrs/month (12 months) | ~$8.50/month |
| DynamoDB | 25 GB (**forever free**) | $0.25/GB after 25GB |
| S3 | 5 GB (12 months) | ~$0.023/GB |
| Data Transfer | 15 GB out (12 months) | $0.09/GB |
| **Total** | **$0 for 12 months** | **~$10-12/month** |

External services:
- Pinecone: Free tier (100K vectors) or paid
- Google Gemini API: Pay per use (~$0.001/query)

## Troubleshooting

### API not starting
```bash
sudo journalctl -u legal-api -n 50
# Check for missing environment variables or import errors
```

### Frontend not building
```bash
cd frontend
npm install
npm run build
# Check for Node.js version issues
```

### Cannot connect from browser
1. Check EC2 Security Group allows ports 3000 and 8000
2. Check services are running: `sudo systemctl status legal-api legal-frontend`
3. Check EC2 public IP hasn't changed (use Elastic IP for permanence)

### DynamoDB connection issues
```bash
# Test AWS credentials
aws sts get-caller-identity
# Should show your IAM user info
```
