import asyncio
import os
import json
import httpx
from typing import List, Optional, Any
from pydantic import BaseModel
from openai import OpenAI

# Assuming these are imported from our local package
from models import CloudAction, AuditAction, FixSecurityGroupAction, EnableS3EncryptionAction, SubmitReportAction, CloudObservation

class StepResult(BaseModel):
    observation: CloudObservation
    reward: float
    done: bool
    info: dict

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
        # Pydantic Union types serialize better with model_dump in v2
        action_dict = action.model_dump() if hasattr(action, "model_dump") else action.dict()
        response = await self.client.post(f"{self.base_url}/step", json=action_dict)
        response.raise_for_status()
        data = response.json()
        return StepResult(**data)

    async def close(self):
        await self.client.aclose()

API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

TASK_NAME = os.getenv("TASK_NAME", "easy_audit")
BENCHMARK = "cloud_audit_env"
MAX_STEPS = 10
TEMPERATURE = 0.0
MAX_TOKENS = 512

SUCCESS_SCORE_THRESHOLD = 0.1

SYSTEM_PROMPT = """
You are a Cloud Security Engineer. Your goal is to audit and remediate a virtual cloud environment.
Tasks include:
1. Finding Security Groups with port 22 open to 0.0.0.0/0.
2. Enabling encryption on S3 buckets.
3. Refactoring IAM policies to remove wildcards ('*').

You must output your next action as a JSON object matching the expected schema.
Example actions:
- {"action": {"action_type": "audit"}}
- {"action": {"sg_id": "sg-1", "port": 22, "cidr_to_remove": "0.0.0.0/0"}}
- {"action": {"bucket_name": "my-bucket"}}
- {"action": {"findings": ["Fixed SG", "Encrypted Bucket"]}}

Always focus on the current task and progress towards 100% compliance.
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
        print("[ERROR] HF_TOKEN or OPENAI_API_KEY environment variable is not set.")
        return

    openai_client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # The Docker container is exposing port 8000
    env_url = os.getenv("ENV_URL", "http://localhost:8000")
    env = AsyncCloudClient(base_url=env_url)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset()
        
        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break
            
            # Agent logic: call LLM with observation
            # Filter observation to avoid passing reward/done back to the agent if not needed
            obs_dict = result.observation.model_dump() if hasattr(result.observation, "model_dump") else result.observation.dict()
            obs_json = json.dumps(obs_dict)
            
            try:
                completion = openai_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Observation: {obs_json}\nDecide your next action."},
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
                # Basic fallback to audit if LLM fails
                action_obj = CloudAction(action=AuditAction())
                action_str = "audit-fallback"
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
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Runtime error: {e}")
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
        await env.close()

if __name__ == "__main__":
    asyncio.run(main())
