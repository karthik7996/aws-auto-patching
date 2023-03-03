import json
import boto3
import logging
import os
from datetime import datetime, date
from botocore.exceptions import ClientError

ssm_client = boto3.client('ssm')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def date_to_str(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()


def lambda_handler(event, context):
    logger.info(json.dumps(event))
    execution_id = event['AutomationId']['AutomationExecutionId']
    try:
        res = ssm_client.describe_automation_executions(
            Filters=[{'Key': 'ExecutionId', 'Values': [execution_id]}]
        )
    except ClientError as e:
        logger.error(e)
        raise Exception('Could not get execution status.')
    logger.info(json.dumps(res, default=date_to_str))
    execution_status = res['AutomationExecutionMetadataList'][0].get(
        'AutomationExecutionStatus')
    execution_status = 'Failed' if execution_status in (
        'TimedOut', 'Cancelled', 'Failed') else execution_status
    new_ami_id = res['AutomationExecutionMetadataList'][0].get(
        'Outputs', {}).get('createImage.ImageId', [[]])[0]
    return {'status': execution_status, 'newAmiID': new_ami_id}
