from typing import List, Optional, Union, Dict
from pydantic import BaseModel, Field

# --- Observation Models ---

class SecurityGroupRule(BaseModel):
    port: int
    cidr: str

class SecurityGroup(BaseModel):
    id: str
    name: str
    ingress_rules: List[SecurityGroupRule]

class S3Bucket(BaseModel):
    name: str
    encrypted: bool

class IAMPolicy(BaseModel):
    id: str
    name: str
    document: str

class CloudObservation(BaseModel):
    security_groups: List[SecurityGroup]
    s3_buckets: List[S3Bucket]
    iam_policies: List[IAMPolicy]
    message: str = "Cloud resources loaded."
    reward: float = 0.0
    done: bool = False
    info: dict = {}

# --- Action Models ---

class AuditAction(BaseModel):
    """Scan and list resources."""
    action_type: str = "audit"

class FixSecurityGroupAction(BaseModel):
    """Remove a specific CIDR rule from a security group."""
    sg_id: str
    port: int
    cidr_to_remove: str

class EnableS3EncryptionAction(BaseModel):
    """Enable server-side encryption for an S3 bucket."""
    bucket_name: str

class UpdateIAMPolicyAction(BaseModel):
    """Update an IAM policy with a new document."""
    policy_id: str
    new_document: str

class SubmitReportAction(BaseModel):
    """Submit the audit results and end the session."""
    findings: List[str]

class CloudAction(BaseModel):
    action: Union[
        AuditAction, 
        FixSecurityGroupAction, 
        EnableS3EncryptionAction, 
        UpdateIAMPolicyAction, 
        SubmitReportAction
    ]

# --- State Model ---

class CloudState(BaseModel):
    task_name: str
    step_count: int
    max_steps: int
    remediated_count: int
    total_resources: int
