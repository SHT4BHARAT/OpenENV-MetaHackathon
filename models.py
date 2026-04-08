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

# --- Unified Action Model ---

class CloudAction(BaseModel):
    """
    Unified action model to resolve union validation issues.
    All specialized fields are optional.
    """
    action_type: str # mandatory: "audit", "fix_sg", "enable_s3_enc", "update_iam", "submit"
    
    # fix_sg fields
    sg_id: Optional[str] = None
    port: Optional[int] = None
    cidr_to_remove: Optional[str] = None
    
    # enable_s3_enc fields
    bucket_name: Optional[str] = None
    
    # update_iam fields
    policy_id: Optional[str] = None
    new_document: Optional[str] = None
    
    # submit fields
    findings: Optional[List[str]] = None

# --- State Model ---

class CloudState(BaseModel):
    task_name: str
    step_count: int
    max_steps: int
    remediated_count: int
    total_resources: int
