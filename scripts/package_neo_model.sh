if [ $# -ne 4 ]; then
  echo 1>&2 "Usage: $0 AWS-PROFILE-NAME S3-BUCKET AWS-REGION SAGEMAKER-ROLE-NAME"
  exit 3
fi

AWS_PROFILE=$1
BUCKET_NAME=$2
AWS_REGION=$3
ROLE_NAME=$4

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME | jq -r .Role.Arn)

PACKAGED_MODEL_NAME=darknet-model
PACKAGED_MODEL_VERSION=1.0
MODEL_PACKAGE=$PACKAGED_MODEL_NAME-$PACKAGED_MODEL_VERSION.tar.gz
COMPILATION_JOB_NAME=jetson-xavier-darknet-001
PACKAGING_JOB_NAME=$COMPILATION_JOB_NAME-packaging

aws sagemaker create-edge-packaging-job --edge-packaging-job-name $PACKAGING_JOB_NAME \
  --compilation-job-name $COMPILATION_JOB_NAME --model-name $PACKAGED_MODEL_NAME --model-version $PACKAGED_MODEL_VERSION \
  --role-arn $ROLE_ARN --output-config "{\"S3OutputLocation\":\"s3:\/\/$BUCKET_NAME\/models\/packaged\/\"}" --region $AWS_REGION --profile $AWS_PROFILE