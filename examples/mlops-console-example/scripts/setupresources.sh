#!/bin/bash
#
# Copyright 2010-2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#

if [ $# -ne 3 ]; then
  echo 1>&2 "Usage: $0 ROLE_ALIAS_NAME IOT_THING_NAME REGION"
  exit 3
fi

# Arguments
ROLE_ALIAS_NAME=$1
echo "ROLE ALIAS: $ROLE_ALIAS_NAME"
IOT_THING_NAME=$2
echo "GREENGRASS CORE THING NAME: $IOT_THING_NAME"
REGION=$3
echo "REGION: $REGION"

# Trust document
ASSUME_POLICY_DOCUMENT="{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"credentials.iot.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"},{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"sagemaker.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"

# Edge Manager device fleet parameters
DEVICE_FLEET_NAME=greengrassv2fleet
DEVICE_NAME=$IOT_THING_NAME

# Get the role name from the IoT Role Alias
IOT_ROLE_ALIAS_IAM_ROLE=$(aws iot describe-role-alias --role-alias $ROLE_ALIAS_NAME --region $REGION | grep roleArn)
IAM_ROLE_ARN=$(echo "$IOT_ROLE_ALIAS_IAM_ROLE" | sed -e 's/\(^.*\"roleArn\"\:\ \"\)\(.*\)\(".*$\)/\2/')
IAM_ROLE_NAME=$(echo "$IOT_ROLE_ALIAS_IAM_ROLE" | sed -e 's/\(^.*role\/\)\(.*\)\(".*$\)/\2/')

echo "IAM Role Name : $IAM_ROLE_NAME"
echo "IAM Role ARN : $IAM_ROLE_ARN"

# Attaching policies to IAM Role
echo "Attaching the following roles: AmazonSageMakerEdgeDeviceFleetPolicy, AmazonSageMakerFullAccess, AmazonS3FullAccess, AWSIoTFullAccess"
aws iam attach-role-policy --role-name $IAM_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonSageMakerEdgeDeviceFleetPolicy

aws iam attach-role-policy --role-name $IAM_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

aws iam attach-role-policy --role-name $IAM_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy --role-name $IAM_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AWSIoTFullAccess

# Update trust relationship
echo "Updating trust relationship"
aws iam update-assume-role-policy --role-name $IAM_ROLE_NAME \
 --policy-document $ASSUME_POLICY_DOCUMENT

DATE=$(date +%s)

# Create edge inference bucket
EDGE_INFERENCE_BUCKET_NAME=$DATE-sagemaker-inference-results
echo "Creating edge inference bucket: $EDGE_INFERENCE_BUCKET_NAME"
aws s3 mb s3://$EDGE_INFERENCE_BUCKET_NAME --region $REGION

#Create greengrass component bucket
GG_COMPONENTS_BUCKET_NAME=$DATE-gg-components
echo "Creating Greengrass components bucket: $GG_COMPONENTS_BUCKET_NAME"
aws s3 mb s3://$GG_COMPONENTS_BUCKET_NAME --region $REGION

# Create device fleet
echo "Creating Edge Manager device fleet $DEVICE_FLEET_NAME"
aws sagemaker create-device-fleet --region $REGION --device-fleet-name $DEVICE_FLEET_NAME \
  --role-arn $IAM_ROLE_ARN --output-config "{\"S3OutputLocation\":\"s3://$EDGE_INFERENCE_BUCKET_NAME\"}"

# Register device
echo "Registering GG Core device $IOT_THING_NAME to Edge Manager device fleet"
aws sagemaker register-devices --region $REGION --device-fleet-name $DEVICE_FLEET_NAME \
  --devices "[{\"DeviceName\":\"$DEVICE_NAME\",\"IotThingName\":\"$IOT_THING_NAME\"}]"