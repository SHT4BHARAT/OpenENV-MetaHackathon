from typing import List, Optional, Union, Dict, Annotated, Literal
from pydantic import BaseModel, Field, Tag

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
    action_type: Literal["audit"] = "audit"

class FixSecurityGroupAction(BaseModel):
    """Remove a specific CIDR rule from a security group."""
    action_type: Literal["fix_sg"] = "fix_sg"
    sg_id: str
    port: int
    cidr_to_remove: str

class EnableS3EncryptionAction(BaseModel):
    """Enable server-side encryption for an S3 bucket."""
    action_type: Literal["enable_s3_enc"] = "enable_s3_enc"
    bucket_name: str

class UpdateIAMPolicyAction(BaseModel):
    """Update an IAM policy with a new document."""
    action_type: Literal["update_iam"] = "update_iam"
    policy_id: str
    new_document: str

class SubmitReportAction(BaseModel):
    """Submit the audit results and end the session."""
    action_type: Literal["submit"] = "submit"
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
