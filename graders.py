from typing import List, Dict
from models import SecurityGroup, S3Bucket, IAMPolicy

class CloudAuditGrader:
    """
    Programmatic graders for CloudAuditEnv tasks.
    Scores performance on a scale of 0.1 - 0.9.
    """

    @staticmethod
    def _safe_score(progress: float, health: float = 1.0) -> float:
        """
        Clamps progress into strictly (0, 1).
        Maps 0.0 -> 0.15 and 1.0 -> 0.85 for a safe buffer.
        """
        if health <= 0: return 0.11 # Minimal non-zero score for failure
        
        score = max(0.0, min(1.0, progress))
        if health < 0.5:
            score *= 0.5
            
        return 0.15 + (score * 0.7)

    @staticmethod
    def _get_val(obj, key, default=None):
        if isinstance(obj, dict): return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def grade_easy_audit(sgs: List, manifest: Dict, health: float) -> float:
        """Easy Task: SG Vulnerabilities relative to manifest."""
        total_vulns = manifest.get("sg_vulns", 1)
        remaining = 0
        for sg in sgs:
            rules = CloudAuditGrader._get_val(sg, "ingress_rules", [])
            for r in rules:
                port = CloudAuditGrader._get_val(r, "port")
                cidr = CloudAuditGrader._get_val(r, "cidr")
                if port in [22, 3389] and cidr == "0.0.0.0/0":
                    remaining += 1
        
        progress = max(0.0, (total_vulns - remaining) / float(total_vulns or 1))
        return CloudAuditGrader._safe_score(progress, health)

    @staticmethod
    def grade_medium_remediation(env_state: Dict) -> float:
        """Medium Task: Balanced remediation across S3, RDS, and EBS."""
        manifest = env_state.get('vulnerability_manifest', {})
        health = env_state.get('health_score', 1.0)
        
        # S3 progress
        s3_total = manifest.get("s3_vulns", 1)
        s3_remaining = sum(1 for b in env_state.get('s3_buckets', []) if not CloudAuditGrader._get_val(b, "encrypted"))
        s3_progress = max(0.0, (s3_total - s3_remaining) / float(s3_total or 1))
        
        # DB (RDS/EBS) progress
        db_total = manifest.get("rds_vulns", 0) + manifest.get("ebs_vulns", 0)
        db_remaining = sum(1 for r in env_state.get('rds_instances', []) if not CloudAuditGrader._get_val(r, "encrypted"))
        db_remaining += sum(1 for e in env_state.get('ebs_volumes', []) if not CloudAuditGrader._get_val(e, "encrypted"))
        db_progress = 1.0 if db_total == 0 else max(0.0, (db_total - db_remaining) / float(db_total))
        
        combined_progress = (s3_progress + db_progress) / 2.0
        return CloudAuditGrader._safe_score(combined_progress, health)

    @staticmethod
    def grade_hard_iam(policies: List, env_state: Dict) -> float:
        """Hard Task: IAM Refactoring with content validation."""
        manifest = env_state.get('vulnerability_manifest', {})
        required_map = env_state.get('required_iam_perms', {})
        health = env_state.get('health_score', 1.0)
        
        total_vulns = manifest.get("iam_vulns", 1)
        remediated = 0
        
        for p in policies:
            pid = CloudAuditGrader._get_val(p, "id")
            doc = CloudAuditGrader._get_val(p, "document", "")
            required_action = required_map.get(pid)
            is_broad = "*" in doc
            has_required = required_action in doc if required_action else True
            
            if not is_broad and has_required:
                remediated += 1
            elif not has_required:
                remediated -= 0.5
                
        progress = max(0.0, remediated / float(total_vulns or 1))
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
    return 0.15
