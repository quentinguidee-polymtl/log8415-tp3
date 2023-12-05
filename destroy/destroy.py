import logging

import backoff
from botocore.exceptions import ClientError

from deploy.setup import ec2_res

logger = logging.getLogger(__name__)


def destroy_instances():
    instances = ec2_res.instances.filter(
        Filters=[{
            'Name': 'instance-state-name',
            'Values': ['pending', 'running']
        }],
    )
    for inst in instances:
        inst.terminate()


def destroy_keypair():
    pairs = ec2_res.key_pairs.filter(
        KeyNames=["keypair"],
    )
    for pair in pairs:
        pair.delete()


@backoff.on_exception(backoff.constant, ClientError)
def destroy_security_group():
    security_groups = ec2_res.security_groups.filter(
        GroupNames=["security_group"],
    )
    for sg in security_groups:
        sg.delete()


def main():
    destroy_instances()
    destroy_keypair()
    destroy_security_group()
