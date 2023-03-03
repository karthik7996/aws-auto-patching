import json
import datetime
import time
import boto3
import logging
from botocore.exceptions import ClientError

autoscaling = boto3.client('autoscaling')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(json.dumps(event))
    counter = event.get('Instance', {}).get('counter', 0)
    if counter > 10:
        return {'status': 'Failed', 'counter': counter + 1}
    group_names = event.get('targetASG')
    if isinstance(group_names, str):
        group_names = [group_names]
    logger.info(f'Austcaling Group Names: {group_names}')
    if not group_names:
        return 'ASG does not exist'
    groups = autoscaling.describe_auto_scaling_groups(
        AutoScalingGroupNames=group_names).get('AutoScalingGroups')
    instance_state = groups[0].get('Instances', [{}])[0].get('LifecycleState')
    return {'status': instance_state, 'counter': counter + 1}
