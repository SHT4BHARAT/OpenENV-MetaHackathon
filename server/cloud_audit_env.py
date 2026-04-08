import json
from typing import List, Tuple
from openenv.core.env_server import Environment
from models import (
    CloudAction, CloudObservation, CloudState, 
    SecurityGroup, SecurityGroupRule, S3Bucket, IAMPolicy,
    AuditAction, FixSecurityGroupAction, EnableS3EncryptionAction, 
    UpdateIAMPolicyAction, SubmitReportAction
)

class CloudAuditEnv(Environment):
    def __init__(self):
        super().__init__()
        self.max_steps = 10
        self.reset()

    def reset(self) -> CloudObservation:
        self.step_count = 0
        self.remediated_count = 0
        self.done = False
        
        # Mocking cloud resources
        self.sgs = [
            SecurityGroup(id="sg-1", name="public-ssh", ingress_rules=[
                SecurityGroupRule(port=22, cidr="0.0.0.0/0"),
                SecurityGroupRule(port=80, cidr="0.0.0.0/0")
            ]),
            SecurityGroup(id="sg-2", name="internal", ingress_rules=[
                SecurityGroupRule(port=3306, cidr="10.0.0.0/16")
            ])
        ]
        self.buckets = [
            S3Bucket(name="customer-data", encrypted=False),
            S3Bucket(name="public-assets", encrypted=True)
        ]
        self.policies = [
            IAMPolicy(id="p-1", name="OverPrivilegedPolicy", document=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]
            }))
        ]
        
        self.initial_vulns = self._count_vulnerabilities()
        return self._get_observation("Environment reset. Audit pending.", reward=0.0, done=False)

    def step(self, action: CloudAction) -> Tuple[CloudObservation, float, bool, dict]:
        self.step_count += 1
        reward = 0.0
        message = ""

        if self.step_count >= self.max_steps:
            self.done = True
            message = "Max steps reached."

        if isinstance(action, AuditAction):
            message = f"Audit complete. Found {self._count_vulnerabilities()} issues."
            reward = 0.05 # Small reward for auditing
        
        elif isinstance(action, FixSecurityGroupAction):
            found = False
            for sg in self.sgs:
                if sg.id == action.sg_id:
                    original_len = len(sg.ingress_rules)
                    sg.ingress_rules = [r for r in sg.ingress_rules if not (r.port == action.port and r.cidr == action.cidr_to_remove)]
                    if len(sg.ingress_rules) < original_len:
                        reward = 0.2
                        self.remediated_count += 1
                        message = f"Fixed Security Group {action.sg_id}."
                        found = True
                    break
            if not found:
                message = f"Security Group {action.sg_id} or rule not found."

        elif isinstance(action, EnableS3EncryptionAction):
            for bucket in self.buckets:
                if bucket.name == action.bucket_name:
                    if not bucket.encrypted:
                        bucket.encrypted = True
                        reward = 0.2
                        self.remediated_count += 1
                        message = f"Enabled encryption for bucket {action.bucket_name}."
                    else:
                        message = f"Bucket {action.bucket_name} already encrypted."
                    break
            else:
                message = f"Bucket {action.bucket_name} not found."

        elif isinstance(action, UpdateIAMPolicyAction):
            # Simple check for least privilege (removing "*" action)
            for policy in self.policies:
                if policy.id == action.policy_id:
                    if "*" not in action.new_document:
                        policy.document = action.new_document
                        reward = 0.5 # High reward for hard task
                        self.remediated_count += 1
                        message = "IAM Policy updated to least privilege."
                    else:
                        message = "New policy still too broad."
                    break

        elif isinstance(action, SubmitReportAction):
            self.done = True
            final_vulns = self._count_vulnerabilities()
            if final_vulns == 0:
                reward = 1.0 # Bonus for perfect run
                message = "All vulnerabilities remediated. Perfect audit."
            else:
                message = f"Report submitted. {final_vulns} vulnerabilities still remaining."

        obs = self._get_observation(message, reward=reward, done=self.done)
        return obs, reward, self.done, {}

    @property
    def state(self) -> CloudState:
        return CloudState(
            task_name="Cloud Security Audit",
            step_count=self.step_count,
            max_steps=self.max_steps,
            remediated_count=self.remediated_count,
            total_resources=len(self.sgs) + len(self.buckets) + len(self.policies)
        )

    def _get_observation(self, message: str, reward: float = 0.0, done: bool = False) -> CloudObservation:
        return CloudObservation(
            security_groups=self.sgs,
            s3_buckets=self.buckets,
            iam_policies=self.policies,
            message=message,
            reward=reward,
            done=done,
            info={}
        )

    def _count_vulnerabilities(self) -> int:
        count = 0
        for sg in self.sgs:
            for rule in sg.ingress_rules:
                if rule.port == 22 and rule.cidr == "0.0.0.0/0":
                    count += 1
        for bucket in self.buckets:
            if not bucket.encrypted:
                count += 1
        for policy in self.policies:
            if "*" in policy.document:
                count += 1
        return count
