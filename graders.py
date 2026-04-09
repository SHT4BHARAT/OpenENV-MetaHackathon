from typing import List, Dict
from models import SecurityGroup, S3Bucket, IAMPolicy

class CloudAuditGrader:
    """
    Programmatic graders for CloudAuditEnv tasks.
    Scores performance on a scale of 0.0 - 1.0.
    """

    @staticmethod
    def _safe_score(progress: float, health: float = 1.0) -> float:
        """
        Clamps progress into strictly (0, 1).
        Applies health multiplier:
        - Health < 50% -> 0.5x multiplier
        - Health = 0% -> 0.0 total
        """
        if health <= 0: return 0.01 # Minimal non-zero score for total failure
        
        score = progress
        if health < 0.5:
            score *= 0.5
            
        return 0.1 + (score * 0.8)

    @staticmethod
    def grade_easy_audit(sgs: List[SecurityGroup], manifest: Dict, health: float) -> float:
        """Easy Task: SG Vulnerabilities relative to manifest."""
        total_vulns = manifest.get("sg_vulns", 1)
        remaining = sum(1 for sg in sgs for r in sg.ingress_rules if r.port in [22, 3389] and r.cidr == "0.0.0.0/0")
        
        progress = max(0.0, (total_vulns - remaining) / float(total_vulns))
        return CloudAuditGrader._safe_score(progress, health)

    @staticmethod
    def grade_medium_remediation(env_state: Dict) -> float:
        """Medium Task: Balanced remediation across S3, RDS, and EBS."""
        manifest = env_state['vulnerability_manifest']
        health = env_state['health_score']
        
        # S3 progress
        s3_total = manifest.get("s3_vulns", 1)
        s3_remaining = sum(1 for b in env_state['s3_buckets'] if not b.encrypted)
        s3_progress = max(0.0, (s3_total - s3_remaining) / float(s3_total))
        
        # DB (RDS/EBS) progress
        db_total = manifest.get("rds_vulns", 0) + manifest.get("ebs_vulns", 0)
        db_remaining = sum(1 for r in env_state.get('rds_instances', []) if not r.encrypted)
        db_remaining += sum(1 for e in env_state.get('ebs_volumes', []) if not e.encrypted)
        db_progress = 1.0 if db_total == 0 else max(0.0, (db_total - db_remaining) / float(db_total))
        
        combined_progress = (s3_progress + db_progress) / 2.0
        return CloudAuditGrader._safe_score(combined_progress, health)

    @staticmethod
    def grade_hard_iam(policies: List[IAMPolicy], env_state: Dict) -> float:
        """Hard Task: IAM Refactoring with content validation."""
        manifest = env_state['vulnerability_manifest']
        required_map = env_state.get('required_iam_perms', {})
        health = env_state['health_score']
        
        total_vulns = manifest.get("iam_vulns", 1)
        remediated = 0
        
        for p in policies:
            required_action = required_map.get(p.id)
            is_broad = "*" in p.document
            has_required = required_action in p.document if required_action else True
            
            # Policy is actually remediated ONLY if it's no longer broad AND still has required access
            if not is_broad and has_required:
                remediated += 1
            # If the user deleted the required access, they failed this policy
            elif not has_required:
                remediated -= 0.5 # Penalty for breaking access
                
        progress = max(0.0, remediated / float(total_vulns))
        return CloudAuditGrader._safe_score(progress, health)

def get_task_score(task_name: str, env_state: Dict) -> float:
    """Entry point for evaluation scripts."""
    manifest = env_state.get('vulnerability_manifest', {})
    health = env_state.get('health_score', 1.0)
    
    if task_name == "easy_audit":
        return CloudAuditGrader.grade_easy_audit(
            env_state.get('security_groups', []), 
            manifest, 
            health
        )
    elif task_name == "medium_remediation":
        return CloudAuditGrader.grade_medium_remediation(env_state)
    elif task_name == "hard_iam_refactor":
        return CloudAuditGrader.grade_hard_iam(
            env_state.get('iam_policies', []), 
            env_state
        )
    return 0.1
