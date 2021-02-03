if [ $# -ne 4 ]; then
  echo 1>&2 "Usage: $0 AWS-PROFILE-NAME COMPONENT_NAME COMPONENT_VERSION AWS_REGION"
  exit 3
fi

AWS_PROFILE=$1
COMPONENT_NAME=$2
COMPONENT_VERSION=$3
AWS_REGION=$4

ACCOUNT=$(aws sts get-caller-identity --profile $AWS_PROFILE | jq -r '.Account')

aws greengrassv2 delete-component --profile $AWS_PROFILE --arn arn:aws:greengrass:$AWS_REGION:$ACCOUNT:components:$COMPONENT_NAME:versions:$COMPONENT_VERSION --region $AWS_REGION
