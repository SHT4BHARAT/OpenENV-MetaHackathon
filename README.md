---
title: OpenEnv CloudAudit
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---
# OpenENV MetaHackathon: CloudAuditEnv 🚀


Welcome to **CloudAuditEnv**, a dynamic cloud security assessment environment built strictly utilizing the [OpenEnv Framework](https://github.com/meta-pytorch/OpenEnv). This environment challenges Large Language Models to autonomously navigate a mock cloud infrastructure, pinpointing and remediating specific security vulnerabilities.

This project was developed for the **OpenENV MetaHackathon**.

#### [MODIFY] [README.md](file:///d:/HackaThon/OpenENV%20hackathon/README.md)
## 🛡️ The Mission

The agent takes on the persona of a Cloud Security Engineer in a high-density mock environment (13 total resources). The mission involves:

1.  **Security Groups (5 total)**: Audit ingress rules across multiple groups. Surgically remove overly permissive SSH (`22`) and RDP (`3389`) CIDR blocks (e.g., `0.0.0.0/0`).
2.  **S3 Buckets (5 total)**: Enforce server-side encryption across multiple data pools (`customer-logs`, `billing-reports`, etc.).
3.  **IAM Policies (3 total)**: Apply the principle of least privilege by stripping wildcard (`*`) access from JSON policy documents.

The environment is designed to be challenging; a score strictly between **0.0 and 1.0** represents realistic agent performance in an complex audit cycle.

## 🏗️ Technical Architecture

CloudAuditEnv operates fundamentally via a standard containerized HTTP server exposing the core OpenEnv Endpoints: `/reset`, `/step`, `/state`, and `/schema`.

### The Unified Action Model
To guarantee stable JSON validation across different Pydantic parsing engines, the environment implements a **Flat Unified Model**. The Agent communicates using a flat `JSON` dictionary identified by an `action_type`.

**Expected Agent Output Payload (Examples)**:
```json
{"action_type": "audit"}
{"action_type": "fix_sg", "sg_id": "sg-1", "port": 22, "cidr_to_remove": "0.0.0.0/0"}
{"action_type": "enable_s3_enc", "bucket_name": "customer-data"}
{"action_type": "update_iam", "policy_id": "p-1", "new_document": "{\"Version\": \"2012-10-17\", \"Statement\": []}"}
{"action_type": "submit", "findings": ["Remediated SG port 22"]}
```

---

## 💻 Quick Start & Evaluation

### 1. Run the Environment Server Locally

We strictly utilize Docker to manage dependencies.

```bash
# Build the Docker image
docker build -t cloudaudit .

# Run the OpenEnv server on HF Spaces default port (7860)
docker run -d -p 7860:7860 cloudaudit
```

### 2. Launch the Baseline Agent

We have provided a robust asynchronous `httpx` baseline agent (`inference.py`) capable of interfacing with Hugging Face's serverless endpoints. 

You will need a Hugging Face Token with "Inference/Write" permissions.

```bash
# Set your LLM Provider endpoint and Model
export HF_TOKEN="your_hugging_face_token"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"

# Start the audit
python inference.py
```

### 📜 Expected Agent Output
The baseline `inference.py` evaluates all 3 tasks. Example output:
```bash
[START] task=easy_audit env=cloud_audit_env model=Qwen/Qwen2.5-72B-Instruct
...
[END] success=true steps=10 score=0.622 rewards=0.08,0.08,0.08...

[START] task=medium_remediation env=cloud_audit_env model=Qwen/Qwen2.5-72B-Instruct
...
[END] success=true steps=10 score=0.711 rewards=0.08,0.08,0.08...

[START] task=hard_iam_refactor env=cloud_audit_env model=Qwen/Qwen2.5-72B-Instruct
...
[END] success=true steps=10 score=0.444 rewards=0.08,0.08,0.08...
```
