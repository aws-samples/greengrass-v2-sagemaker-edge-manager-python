if [ $# -ne 4 ]; then
  echo 1>&2 "Usage: $0 AWS-PROFILE-NAME AWS-REGION OUTPUT-S3-BUCKET IOT-THING-NAME"
  exit 3
fi

AWS_PROFILE=$1
AWS_REGION=$2
OUTPUT_BUCKET=$3
IOT_THING_NAME=$4
DEVICE_NAME=sagemaker-ggv2-smem-device-012345678

ROLE_NAME=SageMakerDeviceFleetRole
ASSUME_POLICY_DOCUMENT="{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"credentials.iot.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"},{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"sagemaker.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"
DEVICE_FLEET_NAME=ggv2-smem-fleet


aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document $ASSUME_POLICY_DOCUMENT --profile $AWS_PROFILE

if [[ $? -ne 0 ]]
then
  echo 'Role already exists, continue...'
fi


# Attach IAM policies

aws iam attach-role-policy --profile $AWS_PROFILE --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonSageMakerEdgeDeviceFleetPolicy

aws iam attach-role-policy --profile $AWS_PROFILE --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

aws iam attach-role-policy --profile $AWS_PROFILE --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy --profile $AWS_PROFILE --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AWSIoTFullAccess

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --profile $AWS_PROFILE | jq -r .Role.Arn)

# Create device fleet

aws sagemaker create-device-fleet --profile $AWS_PROFILE --region $AWS_REGION --device-fleet-name $DEVICE_FLEET_NAME \
  --role-arn $ROLE_ARN --output-config "{\"S3OutputLocation\":\"s3://$OUTPUT_BUCKET/collected_sample_data/\"}"

# Register device

aws sagemaker register-devices --profile $AWS_PROFILE --region $AWS_REGION --device-fleet-name $DEVICE_FLEET_NAME \
  --devices "[{\"DeviceName\":\"$DEVICE_NAME\",\"IotThingName\":\"$IOT_THING_NAME\"}]"