import logging

import backoff
from botocore.exceptions import ClientError

from deploy.setup import ec2_res

logger = logging.getLogger(__name__)


def destroy_instances():
    logger.info("Terminating instances")
    instances = ec2_res.instances.filter(
        Filters=[{
            'Name': 'instance-state-name',
            'Values': ['pending', 'running']
        }],
    )
    for inst in instances:
        inst.terminate()


def destroy_keypair():
    try:
        logger.info("Deleting key pair")
        pairs = ec2_res.key_pairs.filter(
            KeyNames=["keypair"],
        )
        for pair in pairs:
            pair.delete()
            logger.info("Key pair deleted")
    except ClientError as e:
        if e.response['Error']['Code'] != 'InvalidKeyPair.NotFound':
            raise
        logger.error("Key pair not found")


@backoff.on_exception(backoff.constant, ClientError)
def destroy_security_group():
    try:
        logger.info("Deleting security group")
        security_groups = ec2_res.security_groups.filter(
            GroupNames=["security_group"],
        )
        for sg in security_groups:
            sg.delete()
            logger.info("Security group deleted")
    except ClientError as e:
        if e.response['Error']['Code'] != 'InvalidGroup.NotFound':
            raise
        logger.info("Security group not found")


def main():
    destroy_instances()
    destroy_keypair()
    destroy_security_group()

    logger.info("Environment destroyed")
