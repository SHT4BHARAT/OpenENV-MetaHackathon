# OpenEnv: Cloud Infrastructure Security Audit (CloudAuditEnv)

Create a production-ready OpenEnv environment that simulates a Cloud Security Engineer's workflow. The environment will challenge agents to audit, remediate, and refactor cloud infrastructure (Security Groups, S3, IAM) for security compliance.

## User Review Required

> [!IMPORTANT]
> **Real-World Task Selection**: I have selected **Cloud Security Auditing**. This satisfies the "real-world utility" (30%) requirement as it's a common enterprise bottleneck.
> **Task Difficulty Progression**:
> - **Easy**: Categorizing pre-identified vulnerabilities.
> - **Medium**: Active remediation (modifying config).
> - **Hard**: Semantic analysis of IAM policies for least-privilege refactoring.
> **Evaluation Check**: The plan includes a `validate-submission.sh` step to confirm the HF Space ping, Docker build, and `openenv validate` pass.

## Proposed Changes

### 1. Environment Core & Logic

#### [NEW] [models.py](file:///d:/HackaThon/OpenENV%20hackathon/models.py)
Define the strongly-typed interface using Pydantic:
- `CloudAction`: Union of discretized actions (e.g., `close_port(sg_id, port)`, `encrypt_bucket(name)`, `submit_policy(json)`).
- `CloudObservation`: Structured view of the "Mock VPC" (resources, current settings, status logs).
- `CloudState`: Internal environment state for tracking progress and episode history.

#### [NEW] [server/cloud_audit_env.py](file:///d:/HackaThon/OpenENV%20hackathon/server/cloud_audit_env.py)
Implementation of the `Environment` base class:
- `reset()`: Generate a deterministic mock infrastructure based on `task_name`.
- `step(action)`: Execute state transitions, calculate partial rewards, and return the `(obs, reward, done, info)` tuple.
- `state()`: Expose metadata for the `state()` endpoint.

#### [NEW] [graders.py](file:///d:/HackaThon/OpenENV%20hackathon/graders.py)
Deterministic scoring logic for 3 tasks:
- **Easy_Audit**: Binary checks for port visibility.
- **Medium_Remediation**: State reconciliation (Target state vs Current state).
- **Hard_IAM**: Policy "Entropy/Risk Score" reduction analysis.
- **Reward Normalization**: Each task defines a `MAX_TOTAL_REWARD` used by `inference.py` to produce a final `[0, 1]` score.

---

### 2. Integration & Compliance

#### [NEW] [openenv.yaml](file:///d:/HackaThon/OpenENV%20hackathon/openenv.yaml)
OpenEnv manifest defining metadata and model paths for the validator.

#### [NEW] [inference.py](file:///d:/HackaThon/OpenENV%20hackathon/inference.py)
The mandatory baseline script:
- Uses `OpenAI` client with `HF_TOKEN` and `API_BASE_URL`.
- Implements strict logging functions: `log_start`, `log_step`, `log_end`.
- **Fields**:
  - `[START]`: task, env, model.
  - `[STEP]`: step, action, reward (2 decimals), done (bool), error (msg/null).
  - `[END]`: success (bool), steps, score (3 decimals), rewards (comma-separated).

#### [NEW] [Dockerfile](file:///d:/HackaThon/OpenENV%20hackathon/Dockerfile)
Multi-stage build to keep image size small:
- Base: `python:3.10-slim`.
- Dependencies: `openenv-core`, `fastapi`, `uvicorn`, `pydantic`, `openai`.
- Entrypoint: Start FastAPI server on port 8000.

---

### 3. Documentation

#### [NEW] [README.md](file:///d:/HackaThon/OpenENV%20hackathon/README.md)
Detailed documentation on:
- Environment motivation.
- Action/Observation space definitions.
- Task descriptions with expected difficulty.
- Implementation of the reward function (partial progress signals).

## Open Questions

> [!WARNING]
> **Mock Data Seed**: Should the environment use a hardcoded seed for the "reproducible scores" requirement, or should the `reset()` be pseudo-random with a task-specific seed? (Default: Task-specific fixed seed).

## Verification Plan

### Automated Tests
1. **Spec Validation**: `openenv validate` (Passes if Pydantic models match the YAML spec).
2. **Container Build**: `docker build -t cloudaudit .` (Confirm successful install of dependencies).
3. **Internal Loop**: Run `python inference.py` locally against the environment server and verify:
   - Output contains perfectly formatted `[START]`, `[STEP]`, `[END]` tags.
   - Reward sum matches the final reported `score` (normalized by `MAX_TOTAL_REWARD`).
4. **Final Gate**: Run `./scripts/validate-submission.sh` to simulate the hackathon's eval runner.

### Manual Verification
- Manually trigger `step()` with invalid actions to ensure `error=<msg>` is correctly captured in logs.
- Verify that `done=true` is emitted when the task is resolved or max steps are reached.
