import json
import datetime
import time
import os
import boto3
import logging
from botocore.exceptions import ClientError
from copy import error

ec2_client = boto3.client('ec2')
autoscaling = boto3.client('autoscaling')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    asg_name = event.get('targetASG')
    str_asg = (" ".join(map(str,asg_name)))

    # Trigger Auto Scaling group Instance Refresh
    trigger_auto_scaling_instance_refresh(str_asg)
    return("Success")

def trigger_auto_scaling_instance_refresh(str_asg, strategy="Rolling",
                                          min_healthy_percentage=90, instance_warmup=300):

    try:
        response = autoscaling.start_instance_refresh(
            AutoScalingGroupName=str_asg,
            Strategy=strategy,
            Preferences={
                'MinHealthyPercentage': min_healthy_percentage,
                'InstanceWarmup': instance_warmup
            })
        logging.info("Triggered Instance Refresh {} for Auto Scaling "
                     "group {}".format(response['InstanceRefreshId'], str_asg))
        
    except ClientError as e:
        logging.error("Unable to trigger Instance Refresh for "
                      "Auto Scaling group {}".format(str_asg))
        raise e
