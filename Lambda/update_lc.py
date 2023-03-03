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
    old_lc = event.get('LaunchConfig', {}).get('oldLc')
    return_msg = ''
    if event.get('Instance', {}).get('status') == 'InService':
        return_msg = f'Delete Old Launch Configuration {old_lc}'
        logger.info(return_msg)
        # Delete manually later for now
        # autoscaling.delete_launch_configuration(LaunchConfigurationName=old_lc)
    elif event.get('Instance', {}).get('status') == 'Failed':
        return_msg = f'Rollback LaunchConfiguratio to {old_lc}'
        logger.info(return_msg)
        autoscaling.update_auto_scaling_group(
            AutoScalingGroupName=event.get('targetASG')[0],
            LaunchConfigurationName=old_lc
        )
    return return_msg
