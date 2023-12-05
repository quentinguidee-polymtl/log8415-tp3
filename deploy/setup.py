import asyncio

import boto3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_ec2.service_resource import KeyPair, Vpc, SecurityGroup, Instance

ec2_cli = boto3.client('ec2')
ec2_res = boto3.resource('ec2')


async def setup():
    vpc = get_default_vpc()
    key_pair = create_key_pair()
    security_group = create_security_group(vpc)
    availability_zone = get_availability_zones()[0]

    instances: list['Instance'] = []

    instances += create_instance("MySQL", security_group, key_pair, availability_zone)

    tasks = [asyncio.to_thread(wait_instance, inst) for inst in instances]
    await asyncio.gather(*tasks)

    return instances


def get_default_vpc() -> 'Vpc':
    vpcs = ec2_cli.describe_vpcs(Filters=[{
        'Name': 'is-default',
        'Values': ['true']
    }])
    return ec2_res.Vpc(vpcs['Vpcs'][0]['VpcId'])


def create_key_pair() -> 'KeyPair':
    key_pair = ec2_res.create_key_pair(KeyName='keypair')
    with open('keypair.pem', 'w') as f:
        f.write(key_pair.key_material)
    return key_pair


def create_security_group(vpc: 'Vpc') -> 'SecurityGroup':
    group = ec2_res.create_security_group(
        GroupName='security_group',
        Description='security_group',
        VpcId=vpc.id
    )
    group.authorize_ingress(
        IpPermissions=[
            {
                "FromPort": 22,
                "ToPort": 22,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
            {
                "FromPort": 3306,
                "ToPort": 3306,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
        ]
    )
    return group


def create_instance(name: str, security_group: 'SecurityGroup', key_pair: 'KeyPair', availability_zone: str):
    return ec2_res.create_instances(
        KeyName=key_pair.key_name,
        SecurityGroupIds=[security_group.id],
        InstanceType='t2.micro',
        ImageId='ami-053b0d53c279acc90',
        Placement={'AvailabilityZone': availability_zone},
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[
            {
                'DeviceName': '/dev/sda1',
                'Ebs': {
                    'DeleteOnTermination': True,
                    'VolumeSize': 15,
                    'VolumeType': 'gp2',
                }
            }
        ],
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{
                'Key': 'Name',
                'Value': name,
            }]
        }]
    )


def wait_instance(inst: 'Instance'):
    inst.wait_until_running()
    inst.reload()


def get_availability_zones():
    zones = []
    for zone in ec2_cli.describe_availability_zones()['AvailabilityZones']:
        if 'ZoneName' in zone:
            zones.append(zone['ZoneName'])
    return zones
