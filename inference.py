import asyncio
import os
import json
import httpx
from typing import List, Optional, Any
from pydantic import BaseModel
from openai import OpenAI

# Unified model imports
from models import CloudAction, CloudObservation

class StepResult(BaseModel):
    observation: CloudObservation
    reward: Optional[float] = 0.0
    done: bool = False
    info: dict = {}

class AsyncCloudClient:
    """Library-agnostic client for CloudAuditEnv using httpx."""
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def reset(self) -> StepResult:
        response = await self.client.post(f"{self.base_url}/reset", json={})
        response.raise_for_status()
        data = response.json()
        return StepResult(**data)
    
    async def step(self, action: CloudAction) -> StepResult:
        # The framework expects the action to be wrapped in an "action" key
        payload = {"action": action.model_dump()}
        response = await self.client.post(f"{self.base_url}/step", json=payload)
        response.raise_for_status()
        data = response.json()
        return StepResult(**data)

    async def close(self):
        await self.client.aclose()

# Credentials and configuration (Strictly utilizing validator-injected env vars)
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

TASK_NAME = os.getenv("TASK_NAME", "easy_audit")
BENCHMARK = "cloud_audit_env"
MAX_STEPS = 30
TEMPERATURE = 0.0
MAX_TOKENS = 512

SUCCESS_SCORE_THRESHOLD = 0.1

SYSTEM_PROMPT = """
You are a Cloud Security Engineer. Your goal is to audit and remediate a production cloud environment.
Environment Details:
- The environment is PROCEDURALLY GENERATED. Resource IDs will change every session.
- Resources: Security Groups, S3 Buckets, RDS Instances, EBS Volumes, IAM Policies.
- CRITICAL: Maintain 'Deployment Health'. If you remove essential rules or permissions, health drops. If health hits 0, the mission fails.

Tasks include:
1. Finding Security Groups with port 22 or 3389 open to 0.0.0.0/0.
2. Enabling encryption on S3, RDS, and EBS resources.
3. Refactoring IAM policies to remove wide wildcards ('*') while PRESERVING required access mentioned in the policy name/tags.

Performance Rule: Output your next action as a FLAT JSON object. 
Example actions:
- {"action_type": "audit"}
- {"action_type": "remediate_all_in_sg", "sg_id": "sg-f3a2"}
- {"action_type": "enable_rds_enc", "rds_id": "db-b4c1"}
- {"action_type": "update_iam", "policy_id": "p-9d2a", "new_document": "{...}"}
- {"action_type": "submit", "findings": ["Remediated multiple SGs", "Encrypted RDS/EBS"]}

Note: Use 'remediate_all_in_sg' to clean a security group efficiently.
"""

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

async def main() -> None:
    if not API_KEY:
        print("[ERROR] API_KEY/HF_TOKEN environment variable is not set.")
        return
    
    if not API_BASE_URL:
        # Fallback only for local testing if not in validator
        print("[DEBUG] No API_BASE_URL provided. Falling back to default.")
        base_url = "https://router.huggingface.co/v1"
    else:
        base_url = API_BASE_URL

    if not MODEL_NAME:
        model_name = "Qwen/Qwen2.5-72B-Instruct"
    else:
        model_name = MODEL_NAME

    openai_client = OpenAI(base_url=base_url, api_key=API_KEY)
    
async def run_episode(openai_client: OpenAI, env: AsyncCloudClient, task_name: str, model_name: str) -> None:
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=model_name)

    try:
        result = await env.reset()
        
        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break
            
            obs_dict = result.observation.model_dump()
            # Remove reward/done/info from prompt context to keep LLM focused on state
            if "reward" in obs_dict: del obs_dict["reward"]
            if "done" in obs_dict: del obs_dict["done"]
            if "info" in obs_dict: del obs_dict["info"]
            
            obs_json = json.dumps(obs_dict)
            
            try:
                completion = openai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Task: {task_name}\nObservation: {obs_json}\nDecide your next action."},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    response_format={ "type": "json_object" }
                )
                action_content = completion.choices[0].message.content
                action_data = json.loads(action_content)
                action_obj = CloudAction(**action_data)
                action_str = json.dumps(action_data)
            except Exception as e:
                action_obj = CloudAction(action_type="audit")
                action_str = '{"action_type": "audit"}'
                print(f"[DEBUG] Action generation error: {e}")

            result = await env.step(action_obj)
            
            reward = result.reward
            done = result.done
            rewards.append(reward)
            steps_taken = step
            
            log_step(step=step, action=action_str, reward=reward, done=done, error=None)
            
            if done:
                break
        
        score = sum(rewards)
        score = min(max(score, 0.0), 0.999) # Enforce strict (0, 1) range
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Runtime error during episode: {e}")
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

async def main() -> None:
    if not API_KEY:
        print("[ERROR] API_KEY/HF_TOKEN environment variable is not set.")
        return
    
    if not API_BASE_URL:
        # Fallback only for local testing
        base_url = "https://router.huggingface.co/v1"
    else:
        base_url = API_BASE_URL

    if not MODEL_NAME:
        model_name = "Qwen/Qwen2.5-72B-Instruct"
    else:
        model_name = MODEL_NAME

    openai_client = OpenAI(base_url=base_url, api_key=API_KEY)
    env_url = os.getenv("ENV_URL", "http://127.0.0.1:7860")
    env = AsyncCloudClient(base_url=env_url)

    # Multi-task evaluation loop
    tasks = ["easy_audit", "medium_remediation", "hard_iam_refactor"]
    for task in tasks:
        await run_episode(openai_client, env, task, model_name)
    
    await env.close()

if __name__ == "__main__":
    asyncio.run(main())
