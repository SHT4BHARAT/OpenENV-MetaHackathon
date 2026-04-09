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

class RDSInstance(BaseModel):
    id: str
    engine: str
    encrypted: bool

class EBSVolume(BaseModel):
    id: str
    encrypted: bool

class IAMPolicy(BaseModel):
    id: str
    name: str
    document: str

class CloudObservation(BaseModel):
    security_groups: List[SecurityGroup]
    s3_buckets: List[S3Bucket]
    rds_instances: List[RDSInstance] = []
    ebs_volumes: List[EBSVolume] = []
    iam_policies: List[IAMPolicy]
    task_description: str = "Perform a cloud security audit and remediate vulnerabilities."
    vulnerability_manifest: Dict[str, int] = {} # e.g. {"sg_vulns": 4, "s3_vulns": 3}
    message: str = "Cloud resources loaded."
    reward: float = 0.0
    health_score: float = 1.0 # 0.0 to 1.0 (AVAILABILITY)
    done: bool = False
    info: dict = {}

# --- Unified Action Model ---

class CloudAction(BaseModel):
    """
    Unified action model to resolve union validation issues.
    All specialized fields are optional.
    """
    action_type: str # "audit", "fix_sg", "remediate_all_in_sg", "enable_s3_enc", "enable_rds_enc", "enable_ebs_enc", "update_iam", "submit"
    
    # Target identifiers
    sg_id: Optional[str] = None
    bucket_name: Optional[str] = None
    policy_id: Optional[str] = None
    rds_id: Optional[str] = None
    ebs_id: Optional[str] = None
    
    # fix_sg specific fields
    port: Optional[int] = None
    cidr_to_remove: Optional[str] = None
    
    # update_iam fields
    new_document: Optional[str] = None
    
    # submit fields
    findings: Optional[List[str]] = None

# --- State Model ---

class CloudState(BaseModel):
    task_name: str
    step_count: int
    max_steps: int
    remediated_count: int
    security_groups: List[SecurityGroup] = []
    s3_buckets: List[S3Bucket] = []
    rds_instances: List[RDSInstance] = []
    ebs_volumes: List[EBSVolume] = []
    iam_policies: List[IAMPolicy] = []
    vulnerability_manifest: Dict[str, int] = {}
    required_iam_perms: Dict[str, str] = {}
    health_score: float = 1.0
