from typing import List, Dict
from models import SecurityGroup, S3Bucket, IAMPolicy

class CloudAuditGrader:
    """
    Programmatic graders for CloudAuditEnv tasks.
    Scores performance on a scale of 0.0 - 1.0.
    """

    @staticmethod
    def grade_easy_audit(sgs: List[SecurityGroup]) -> float:
        """
        Easy Task: Identify open SSH ports.
        Score based on how many rules were removed.
        """
        # In our mock env, only sg-1 has a port 22 open to 0.0.0.0/0
        issues_found = 0
        total_vulns = 1 # Initial port 22 open rule
        
        for sg in sgs:
            for rule in sg.ingress_rules:
                if rule.port == 22 and rule.cidr == "0.0.0.0/0":
                    issues_found += 1
        
        remediated = total_vulns - issues_found
        return max(0.0, float(remediated / total_vulns))

    @staticmethod
    def grade_medium_remediation(sgs: List[SecurityGroup], buckets: List[S3Bucket]) -> float:
        """
        Medium Task: Fix SGs and encrypt S3 buckets.
        """
        sg_score = CloudAuditGrader.grade_easy_audit(sgs)
        
        total_buckets = len(buckets)
        encrypted_count = sum(1 for b in buckets if b.encrypted)
        # One was already encrypted, one was not. 
        # Target: customer-data (unencrypted) -> encrypted
        bucket_score = encrypted_count / total_buckets
        
        return (sg_score + bucket_score) / 2.0

    @staticmethod
    def grade_hard_iam(policies: List[IAMPolicy]) -> float:
        """
        Hard Task: IAM Policy Refactoring.
        Score based on whether '*' action was removed from the target policy.
        """
        for policy in policies:
            if policy.id == "p-1":
                if "*" not in policy.document:
                    return 1.0
                else:
                    return 0.0
        return 0.0

def get_task_score(task_name: str, env_state: Dict) -> float:
    """Entry point for evaluation scripts."""
    if task_name == "easy_audit":
        return CloudAuditGrader.grade_easy_audit(env_state['security_groups'])
    elif task_name == "medium_remediation":
        return CloudAuditGrader.grade_medium_remediation(
            env_state['security_groups'], 
            env_state['s3_buckets']
        )
    elif task_name == "hard_iam_refactor":
        return CloudAuditGrader.grade_hard_iam(env_state['iam_policies'])
    return 0.0
