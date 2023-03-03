import json
import boto3
import logging
import os
from botocore.exceptions import ClientError

ssm_client = boto3.client('ssm')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DOC_NAME = os.getenv('DOC_NAME')


def lambda_handler(event, context):
    logger.info(json.dumps(event))
    try:
        res = ssm_client.start_automation_execution(
            DocumentName=DOC_NAME,
            DocumentVersion='$DEFAULT',
            Parameters=event
        )
    except ClientError as e:
        logger.error(e)
        raise Exception('Could not start automation')
    logger.info(res)
    return res
