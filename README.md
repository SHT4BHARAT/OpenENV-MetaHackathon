# CloudAuditEnv: Cloud Infrastructure Security Audit

CloudAuditEnv is a production-ready OpenEnv environment that simulates a Cloud Security Engineer's workflow. It involves auditing a virtualized cloud environment for security vulnerabilities and performing remediation actions.

## Real-World Task
The environment models common security baseline checks for AWS-like infrastructures, including:
- **Network Security**: Identification of wide-open SSH ports (0.0.0.0/0).
- **Data Protection**: Enabling server-side encryption for S3 buckets.
- **Identity & Access Management (IAM)**: Refactoring wildcard policies (`*`) to follow least-privilege principles.

## Action Space
The agent can interact with the environment using the following actions (defined in `models.py`):
- `AuditAction`: Scans all resources and returns their current configuration.
- `FixSecurityGroupAction(sg_id, port, cidr_to_remove)`: Removes a vulnerable rule.
- `EnableS3EncryptionAction(bucket_name)`: Enables encryption on a non-compliant bucket.
- `UpdateIAMPolicyAction(policy_id, new_document)`: Replaces a policy document with a secure version.
- `SubmitReportAction(findings)`: Ends the episode and submits results.

## Observation Space
The `CloudObservation` model provides:
- A list of `SecurityGroup` objects.
- A list of `S3Bucket` objects.
- A list of `IAMPolicy` objects.
- A descriptive message from the last action.

## Tasks & Difficulties
1. **easy_audit**: Focuses on network security (Security Groups).
2. **medium_remediation**: Combines network security with data protection (S3).
3. **hard_iam_refactor**: Requires semantic reasoning over IAM policy JSONs and log-based refactoring.

## Setup Instructions

### Local Development
1. Install dependencies:
   ```bash
   pip install openenv-core fastapi uvicorn pydantic openai
   ```
2. Start the environment server:
   ```bash
   python -m server.app
   ```
3. Run the baseline evaluation:
   ```bash
   export HF_TOKEN="your_key"
   export API_BASE_URL="llm_endpoint"
   python inference.py
   ```

### Docker
```bash
docker build -t cloudaudit .
docker run -p 8000:8000 cloudaudit
```

## Reward & Scoring
- **Partial Progress**: Rewards are granted per successful remediation (+0.2 - +0.5).
- **Final Score**: The cumulative rewards are normalized in the `[0, 1]` range in `inference.py`.
- **Success Criteria**: A success is defined as a normalized score >= 0.1.
