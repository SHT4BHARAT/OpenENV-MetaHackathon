import pytest
from server.cloud_audit_env import CloudAuditEnv
from models import CloudAction

def test_env_reset():
    env = CloudAuditEnv()
    obs = env.reset(task_name="easy_audit")
    assert obs.task_description == "Find and fix all Security Group rules that allow SSH/RDP access from the public internet (0.0.0.0/0)."
    assert len(obs.security_groups) > 0
    assert obs.health_score == 1.0
    assert not obs.done

def test_env_step_audit():
    env = CloudAuditEnv()
    env.reset()
    action = CloudAction(action_type="audit")
    obs = env.step(action)
    assert obs.message == "Audit log generated."
    assert obs.reward == 0.01
    assert env.step_count == 1

def test_health_penalty_iam():
    env = CloudAuditEnv()
    env.reset(task_name="hard_iam_refactor")
    
    # Get a policy that has a required permission
    p_id = list(env.required_iam_perms.keys())[0]
    required = env.required_iam_perms[p_id]
    
    # Update with an empty document (breaking access)
    action = CloudAction(action_type="update_iam", policy_id=p_id, new_document="{}")
    obs = env.step(action)
    
    assert obs.health_score < 1.0
    assert "CRITICAL" in obs.message

def test_terminal_bonus():
    env = CloudAuditEnv()
    env.reset()
    
    # Spoof remediation count to match initial vulns
    env.remediated_count = env.initial_vulns
    
    action = CloudAction(action_type="submit")
    obs = env.step(action)
    
    assert obs.done
    assert obs.reward == 0.1 # Terminal bonus
    assert "Perfect remediation" in obs.message

def test_grader_resilience():
    from graders import get_task_score
    env = CloudAuditEnv()
    env.reset(task_name="easy_audit")
    
    # Test with object-based state (directly from env)
    score = get_task_score("easy_audit", env.state.__dict__)
    assert 0.15 <= score <= 0.85
    
    # Test with dict-based state (simulating JSON API)
    state_dict = env.state.model_dump()
    score = get_task_score("easy_audit", state_dict)
    assert 0.15 <= score <= 0.85
