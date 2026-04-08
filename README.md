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

## 🛡️ The Mission

The agent takes on the persona of a Cloud Security Engineer. The environment initializes with several mock cloud resources structured logically:

1.  **Security Groups**: The agent must audit ingress rules and surgically remove overly permissive CIDR blocks (e.g., `0.0.0.0/0` on port `22`).
2.  **S3 Buckets**: Unencrypted data at rest is a liability. The agent must enforce server-side encryption across exposed buckets.
3.  **IAM Policies**: The principle of least privilege must be applied, updating JSON policy documents to strip wildcard (`*`) access.

The agent interacts iteratively until a score of `1.0` (all vulnerabilities explicitly remediated) is achieved.

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
```bash
[START] task=easy_audit env=cloud_audit_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action={"action_type": "fix_sg", "sg_id": "sg-1", "port": 22, "cidr_to_remove": "0.0.0.0/0"} reward=0.20 done=false error=null
[STEP] step=2 action={"action_type": "enable_s3_enc", "bucket_name": "customer-data"} reward=0.20 done=false error=null
[STEP] step=3 action={"action_type": "update_iam", ...} reward=0.50 done=false error=null
[END] success=true steps=4 score=1.000
```
