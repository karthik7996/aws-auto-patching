import boto3
import json
import os

ec2_client = boto3.client('ec2')
sns_client = boto3.client('sns')
TOPIC_ARN = os.getenv('TOPIC_ARN')

def handler(event, context):
    print(json.dumps(event))
    msg = json.loads(event.get('Records')[0].get('Sns').get('Message'))
    instance_id = msg.get('EC2InstanceId')
    private_ip = ec2_client.describe_instances(InstanceIds=[instance_id]).get('Reservations',[{}])[0].get('Instances',[{}])[0].get('PrivateIpAddress')
    asg_name = msg.get('AutoScalingGroupName')
    sns_client.publish(
      TopicArn=TOPIC_ARN,
      Message=f'Autoscaling Group {asg_name} launched a new instance.\nInstance IP Address: {private_ip}'
    )
