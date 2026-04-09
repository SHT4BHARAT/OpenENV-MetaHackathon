import json
import random
import uuid
from typing import List, Tuple, Dict
from openenv.core.env_server import Environment
from models import (
    CloudAction, CloudObservation, CloudState, 
    SecurityGroup, SecurityGroupRule, S3Bucket, IAMPolicy,
    RDSInstance, EBSVolume
)

class CloudAuditEnv(Environment):
    def __init__(self):
        super().__init__()
        self.max_steps = 30
        self.reset()

    def reset(self) -> CloudObservation:
        self.step_count = 0
        self.remediated_count = 0
        self.health_score = 1.0
        self.done = False
        
        # Procedural Generation Configuration
        self.sgs: List[SecurityGroup] = []
        self.buckets: List[S3Bucket] = []
        self.rds: List[RDSInstance] = []
        self.ebs: List[EBSVolume] = []
        self.policies: List[IAMPolicy] = []
        
        self.vulnerability_manifest = {"sg_vulns": 0, "s3_vulns": 0, "rds_vulns": 0, "ebs_vulns": 0, "iam_vulns": 0}
        self.essential_rules: Dict[str, List[Tuple[int, str]]] = {} # sg_id -> list of (port, cidr)
        self.required_iam_perms: Dict[str, str] = {} # policy_id -> required substring (e.g. s3:GetObject)
        
        self._generate_procedural_assets()
        
        self.initial_vulns = sum(self.vulnerability_manifest.values())
        return self._get_observation(f"Environment reset. Procedural audit pending with {len(self.sgs) + len(self.buckets) + len(self.rds) + len(self.ebs) + len(self.policies)} resources.", reward=0.0, done=False)

    def _generate_procedural_assets(self):
        # 1. Security Groups (5-7)
        num_sgs = random.randint(5, 7)
        for i in range(num_sgs):
            sg_id = f"sg-{uuid.uuid4().hex[:6]}"
            rules = []
            # Legitimate rule (Essential)
            ess_port = random.choice([443, 8080, 5432])
            rules.append(SecurityGroupRule(port=ess_port, cidr="10.0.0.0/8"))
            self.essential_rules[sg_id] = [(ess_port, "10.0.0.0/8")]
            
            # Vulnerable rule (sometimes)
            if random.random() > 0.3:
                vuln_port = random.choice([22, 3389])
                rules.append(SecurityGroupRule(port=vuln_port, cidr="0.0.0.0/0"))
                self.vulnerability_manifest["sg_vulns"] += 1
            
            self.sgs.append(SecurityGroup(id=sg_id, name=f"group-{i}", ingress_rules=rules))

        # 2. S3 Buckets (4-6)
        num_buckets = random.randint(4, 6)
        for i in range(num_buckets):
            name = f"bucket-{uuid.uuid4().hex[:8]}"
            encrypted = random.choice([True, False])
            if not encrypted: self.vulnerability_manifest["s3_vulns"] += 1
            self.buckets.append(S3Bucket(name=name, encrypted=encrypted))

        # 3. RDS Instances (2-3)
        num_rds = random.randint(2, 3)
        for i in range(num_rds):
            rid = f"db-{uuid.uuid4().hex[:4]}"
            enc = random.choice([True, False])
            if not enc: self.vulnerability_manifest["rds_vulns"] += 1
            self.rds.append(RDSInstance(id=rid, engine="postgres", encrypted=enc))

        # 4. EBS Volumes (2-3)
        num_ebs = random.randint(2, 3)
        for i in range(num_ebs):
            eid = f"vol-{uuid.uuid4().hex[:4]}"
            enc = random.choice([True, False])
            if not enc: self.vulnerability_manifest["ebs_vulns"] += 1
            self.ebs.append(EBSVolume(id=eid, encrypted=enc))

        # 5. IAM Policies (3)
        for i in range(3):
            pid = f"p-{uuid.uuid4().hex[:4]}"
            required = random.choice(["s3:GetObject", "ec2:DescribeInstances", "iam:GetUser"])
            self.required_iam_perms[pid] = required
            
            is_vuln = random.choice([True, False])
            if is_vuln:
                doc = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}
                self.vulnerability_manifest["iam_vulns"] += 1
            else:
                doc = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": required, "Resource": "*"}]}
            
            self.policies.append(IAMPolicy(id=pid, name=f"Policy-{i}", document=json.dumps(doc)))

    def step(self, action: CloudAction) -> CloudObservation:
        self.step_count += 1
        reward = 0.0
        message = ""

        if self.step_count >= self.max_steps:
            self.done = True
            message = "Max steps reached."

        at = action.action_type
        fix_reward_increment = 0.8 / max(1, self.initial_vulns)
        
        if at == "audit":
            message = "Audit log generated."
            reward = 0.01
        
        elif at == "fix_sg":
            if action.sg_id and action.port is not None and action.cidr_to_remove:
                for sg in self.sgs:
                    if sg.id == action.sg_id:
                        # Check for availability penalty (removing essential rule)
                        if (action.port, action.cidr_to_remove) in self.essential_rules.get(sg.id, []):
                            self.health_score -= 0.2
                            message = f"CRITICAL: Removed essential rule on {sg.id}! Availability decreased."
                        
                        original_len = len(sg.ingress_rules)
                        old_vulns = self._check_sg_vulns(sg)
                        sg.ingress_rules = [r for r in sg.ingress_rules if not (r.port == action.port and r.cidr == action.cidr_to_remove)]
                        new_vulns = self._check_sg_vulns(sg)
                        
                        if new_vulns < old_vulns:
                            reward = fix_reward_increment
                            self.remediated_count += 1
                            message = message or f"Fixed rule on {sg.id}."
                        break

        elif at == "remediate_all_in_sg":
            if action.sg_id:
                for sg in self.sgs:
                    if sg.id == action.sg_id:
                        vulns = self._check_sg_vulns(sg)
                        if vulns > 0:
                            sg.ingress_rules = [r for r in sg.ingress_rules if not (r.port in [22, 3389] and r.cidr == "0.0.0.0/0")]
                            reward = fix_reward_increment * vulns
                            self.remediated_count += vulns
                            message = f"Batch remediated {vulns} issues in {sg.id}."
                        break

        elif at == "enable_s3_enc":
            for b in self.buckets:
                if b.name == action.bucket_name and not b.encrypted:
                    b.encrypted = True
                    reward = fix_reward_increment
                    self.remediated_count += 1
                    message = f"Encrypted bucket {b.name}."
                    break

        elif at == "enable_rds_enc":
            for db in self.rds:
                if db.id == action.rds_id and not db.encrypted:
                    db.encrypted = True
                    reward = fix_reward_increment
                    self.remediated_count += 1
                    message = f"Encrypted RDS {db.id}."
                    break

        elif at == "enable_ebs_enc":
            for vol in self.ebs:
                if vol.id == action.ebs_id and not vol.encrypted:
                    vol.encrypted = True
                    reward = fix_reward_increment
                    self.remediated_count += 1
                    message = f"Encrypted EBS {vol.id}."
                    break

        elif at == "update_iam":
            for p in self.policies:
                if p.id == action.policy_id:
                    # Check for availability penalty (missing required perm)
                    required = self.required_iam_perms.get(p.id)
                    if required and required not in (action.new_document or ""):
                        self.health_score -= 0.3
                        message = f"CRITICAL: IAM update broke required service access for {p.id}!"
                    
                    was_vuln = "*" in p.document
                    p.document = action.new_document or ""
                    is_vuln = "*" in p.document
                    if was_vuln and not is_vuln:
                        reward = fix_reward_increment
                        self.remediated_count += 1
                        message = message or f"Refactored policy {p.id} to least privilege."
                    break

        elif at == "submit":
            self.done = True
            message = "Audit report submitted."

        # Apply Health Multiplier and Termination
        if self.health_score <= 0:
            self.health_score = 0.0
            self.done = True
            reward = 0.0
            message = "CRITIAL FAILURE: Production environment is offline due to misconfiguration. Mission failed."
        
        final_reward = reward
        if self.health_score < 0.5:
            final_reward *= 0.5
        
        obs = self._get_observation(message, reward=final_reward, done=self.done)
        obs.health_score = self.health_score
        return obs

    def _check_sg_vulns(self, sg: SecurityGroup) -> int:
        return sum(1 for r in sg.ingress_rules if r.port in [22, 3389] and r.cidr == "0.0.0.0/0")

    @property
    def state(self) -> CloudState:
        return CloudState(
            task_name="Production Cloud Security Audit",
            step_count=self.step_count,
            max_steps=self.max_steps,
            remediated_count=self.remediated_count,
            total_resources=len(self.sgs) + len(self.buckets) + len(self.rds) + len(self.ebs) + len(self.policies),
            vulnerability_manifest=self.vulnerability_manifest,
            required_iam_perms=self.required_iam_perms,
            health_score=self.health_score
        )

    def _get_observation(self, message: str, reward: float = 0.0, done: bool = False) -> CloudObservation:
        return CloudObservation(
            security_groups=self.sgs,
            s3_buckets=self.buckets,
            rds_instances=self.rds,
            ebs_volumes=self.ebs,
            iam_policies=self.policies,
            message=message,
            reward=reward,
            health_score=self.health_score,
            done=done,
            info={}
        )
