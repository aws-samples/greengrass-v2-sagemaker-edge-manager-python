if [ $# -ne 5 ]; then
  echo 1>&2 "Usage: $0 AWS-PROFILE-NAME S3-BUCKET AWS-REGION SAGEMAKER-ROLE-NAME TARGET-DEVICE"
  exit 3
fi

AWS_PROFILE=$1
BUCKET_NAME=$2
AWS_REGION=$3
ROLE_NAME=$4
TARGET_DEVICE=$5

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME | jq -r .Role.Arn)

aws sagemaker create-compilation-job --compilation-job-name jetson-xavier-darknet-001 --role-arn $ROLE_ARN \
  --input-config "{\"S3Uri\": \"s3:\/\/$BUCKET_NAME\/models\/yolo3-tiny.tar.gz\",\"DataInputConfig\": \"{\\\"data\\\":[1,3,416,416]}\",\"Framework\": \"DARKNET\"}" \
  --output-config "{\"S3OutputLocation\":\"s3:\/\/$BUCKET_NAME\/models\/neo-compiled\/\",\"TargetDevice\":\"$TARGET_DEVICE\"}" \
  --stopping-condition "{\"MaxWaitTimeInSeconds\":60,\"MaxRuntimeInSeconds\":900}" --profile $AWS_PROFILE --region $AWS_REGION


