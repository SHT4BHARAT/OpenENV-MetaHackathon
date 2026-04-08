import asyncio
import os
import textwrap
import json
from typing import List, Optional
from openai import OpenAI

# Assuming these are imported from our local package
from models import CloudAction, AuditAction, FixSecurityGroupAction, EnableS3EncryptionAction, SubmitReportAction
# In a real OpenEnv setup, the Env class is often auto-generated or provided by openenv-core
# For this baseline, we'll use a mock client that would normally wrap the FastAPI server
# However, to be fully compliant with the 'from_docker_image' example:
from openenv.core.http_env_client import HTTPEnvClient

class CloudAuditClient(HTTPEnvClient):
    """Client-side wrapper for CloudAuditEnv."""
    async def reset(self):
        return await super().reset()
    
    async def step(self, action: CloudAction):
        return await super().step(action.dict())

IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

TASK_NAME = os.getenv("TASK_NAME", "easy_audit")
BENCHMARK = "cloud_audit_env"
MAX_STEPS = 10
TEMPERATURE = 0.0 # Audit tasks usually require precision
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
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # In the actual evaluation, this would point to the Docker container
    # For baseline, we assume the environment is running at localhost:8000
    env_url = f"http://localhost:8000"
    env = CloudAuditClient(base_url=env_url)

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
            
            # Simple agent logic: call LLM with observation
            obs_json = json.dumps(result.observation.dict())
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Observation: {obs_json}\nDecide your next action."},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    response_format={ "type": "json_object" }
                )
                action_data = json.loads(completion.choices[0].message.content)
                action_obj = CloudAction(**action_data)
                action_str = json.dumps(action_data)
            except Exception as e:
                action_obj = CloudAction(action=AuditAction()) # Fallback
                action_str = "audit-fallback"
                print(f"[DEBUG] Error generating action: {e}")

            result = await env.step(action_obj)
            
            reward = result.reward or 0.0
            done = result.done
            rewards.append(reward)
            steps_taken = step
            
            log_step(step=step, action=action_str, reward=reward, done=done, error=None)
            
            if done:
                break
        
        # Calculate final score (normalized to [0, 1])
        # Max reward per step is variable, but graders return a final 1.0 for success.
        # We can use the last reward or a cumulative normalized score.
        score = sum(rewards) # Simplified for baseline
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Runtime error: {e}")
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    asyncio.run(main())
