import json
import datetime
import time
import boto3
import logging
from botocore.exceptions import ClientError
from copy import error

instance_name = ''
ec2_client = boto3.client('ec2')
autoscaling = boto3.client('autoscaling')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

print('Loading function')

current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')


def create_tags(instance_id, group_name):
    # Return List of Tags assigned to new AMI
    # If the given instance is not runnig, Return None
    instance_name = ''
    res = ec2_client.describe_instances(InstanceIds=[instance_id])
    instance = res['Reservations'][0]['Instances'][0]
    instance_state = instance.get('State', {}).get('Name')

    if instance_state != 'running':
        return None
    try:
        instance_name = list(filter(lambda t: t['Key'] == 'Name', instance['Tags']))[
            0].get('Value')
    except IndexError:
        logger.error(IndexError)

    if not instance_name:
        instance_name = 'Unknown'
    instance_type = instance['InstanceType']
    instance_ip_address = instance['PrivateIpAddress']
    instance_subnet = instance['SubnetId']
    instance_groups = ' '.join([g['GroupId']
                                for g in instance['SecurityGroups']])
    ami_name = "AMI Backup of " + group_name + " taken at " + current_timestamp
    return {'Tags': [
            {'Key': 'Name', 'Value': ami_name},
            {'Key': 'DeleteOn', 'Value': '12-31-2099'},
            {'Key': 'Creator', 'Value': 'Lambda'},
            {'Key': 'Type', 'Value': instance_type},
            {'Key': 'IPAddress', 'Value': instance_ip_address},
            {'Key': 'Subnet', 'Value': instance_subnet},
            {'Key': 'SecurityGroups', 'Value': instance_groups},
            {'Key': 'Status', 'Value': 'Latest'},
            {'Key': 'InstanceID', 'Value': instance_id},
            {'Key': 'InstanceName', 'Value': instance_name}],
            'InstanceName': instance_name}


def repalce_image_tags(tags, instance_name, retention_days, image_id):
    # Replacing current latest image tags
    delete_date = datetime.date.today() + datetime.timedelta(days=int(retention_days))
    delete_timestamp = delete_date.strftime('%m-%d-%Y')
    latest = ec2_client.describe_images(
        Filters=[{'Name': 'tag:Status', 'Values': ['Latest']},
                 {'Name': 'tag:DeleteOn', 'Values': ['12-31-2099']},
                 {'Name': 'tag:InstanceName', 'Values': [instance_name]}]).get('Images')

    if latest:
        latest_ami_id = latest[0].get('ImageId')
        try:
            ec2_client.delete_tags(
                Resources=[latest_ami_id],
                Tags=[
                    {'Key': 'Status', 'Value': 'Latest'},
                    {'Key': 'DeleteOn', 'Value': '12-31-2099'}
                ]
            )
            ec2_client.create_tags(
                Resources=[latest_ami_id],
                Tags=[{'Key': 'DeleteOn', 'Value': delete_timestamp}]
            )
        except Exception as e:
            print(e)
            raise Exception('Failed AMI tagging.')
    ec2_client.create_tags(Resources=[image_id], Tags=tags['Tags'])


def update_asg(group_name, instance_name, instance_id, image_id):
    # Create a new Launch Configuration and update Austoscaling group withe latest AMI
    # Return Launch Configuration name
    new_lc_name = 'LC ' + group_name + ' ' + current_timestamp
    autoscaling.create_launch_configuration(
        InstanceId=instance_id,
        LaunchConfigurationName=new_lc_name,
        ImageId=image_id)
    autoscaling.update_auto_scaling_group(
        AutoScalingGroupName=group_name, LaunchConfigurationName=new_lc_name)
    return new_lc_name


def lambda_handler(event, context):
    logger.info(json.dumps(event))
    # Autoscaling group name comes in event
    # if this is invoked by SSM Automation
    # Else, get Autoscaling groups enabled backup
    group_names = event.get('targetASG')
    if isinstance(group_names, str):
        group_names = [group_names]
    logger.info(f'Austcaling Group Names: {group_names}')
    if not group_names:
        return 'ASG does not exist'

    groups = autoscaling.describe_auto_scaling_groups(
        AutoScalingGroupNames=group_names).get('AutoScalingGroups')

    for group in groups:
        group_name = group['AutoScalingGroupName']
        logger.info(f'Start processing {group_name}')
        try:
            instance_id = group['Instances'][0]['InstanceId']
        except IndexError:
            return 'No instance in the autoscaling group'

        # Create tags to assign to the new AMI
        # create_tags returns None if the instance is not running
        tags = create_tags(instance_id, group_name)                             #added the line
        if not tags:
            logger.info(f'{instance_id} is not in running state and skipped.')
            continue
        try:
            retention_days = list(filter(lambda t: t['Key'] == 'Retention', group['Tags']))[
                0].get('Value')
        except IndexError:
            retention_days = 90
        instance_name = tags['InstanceName']
        # AMI was created by SSM Automation
        image_id = event.get('AutomationStatus').get('newAmiID')
        repalce_image_tags(tags, instance_name, retention_days, image_id)
        # Create LaunchConfiguration with the new AMI
        # And update Autoscaling Group
        new_lc_name = update_asg(
            group_name, instance_name, instance_id, image_id)
        logger.info(
            f'New Launch Configuration {new_lc_name} with AMI {image_id} for {group_name}')
        #logger.info(f"Delete Current Launch Configuration {group['LaunchConfigurationName']}")
        # Delete old LaunchConfiguration
        # autoscaling.delete_launch_configuration(LaunchConfigurationName=group['LaunchConfigurationName'])
        ec2_client.stop_instances(InstanceIds=[instance_id])
        return {'oldLc': group['LaunchConfigurationName'], 'newLc': new_lc_name}
