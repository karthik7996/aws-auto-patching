import json
import datetime
import boto3
import logging
import os
from botocore.exceptions import ClientError

autoscaling = boto3.client('autoscaling')
sfn_client = boto3.client('stepfunctions')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

STATE_MACHINE_ARN = os.getenv('STATE_MACHINE_ARN')
#SUBNET_ID = os.getenv('SUBNET_ID')


def get_groups():
    # Return List of Autoscaling group names that backup is enabled
    groups = autoscaling.describe_auto_scaling_groups().get('AutoScalingGroups')
    backup_groups = []
    for group in groups:
        if group.get('Instances'):
            for tag in group.get('Tags', []):
                if tag.get('Key') == 'AutoPatch' and tag.get('Value') == 'True':
                    ami_id = autoscaling.describe_launch_configurations(
                        LaunchConfigurationNames=[
                            group.get('LaunchConfigurationName')]
                    ).get('LaunchConfigurations')[0].get('ImageId')
                    backup_groups.append(
                        {'targetASG': [group['AutoScalingGroupName']],
                        'sourceAMIid': [ami_id]})
    return backup_groups


def lambda_handler(event, context):
    logger.info(json.dumps(event))

    groups = get_groups()
    if not groups:
        return 'No Autoscaling group found.'
    today = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M')
    for group in groups:
        group_name = group['targetASG'][0]
        logger.info(f'Processing {group_name}')
        try:
            sfn_client.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=f'AMIPatch-for-{group_name}-{today}',
                input=(json.dumps(group))
            )
        except ClientError as e:
            logger.error(e)
            raise Exception('Could not start Step Functions.')
