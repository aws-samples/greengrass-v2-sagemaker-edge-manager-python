if [ $# -ne 2 ]; then
  echo 1>&2 "Usage: $0 AWS-PROFILE-NAME ROLE-NAME"
  exit 3
fi

AWS_PROFILE=$1
SM_ROLE_NAME=$2

aws iam create-role --profile $AWS_PROFILE --role-name $SM_ROLE_NAME --assume-role-policy-document "{\"Version\": \"2012-10-17\",\"Statement\":[{\"Effect\": \"Allow\",\"Principal\":{\"Service\":\"sagemaker.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"

aws iam attach-role-policy --profile $AWS_PROFILE --role-name $SM_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

aws iam attach-role-policy --profile $AWS_PROFILE --role-name $SM_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess