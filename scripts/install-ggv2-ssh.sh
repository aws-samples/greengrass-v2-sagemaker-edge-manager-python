if [ $# -ne 5 ]; then
  echo 1>&2 "Usage: $0 AWS-PROFILE-NAME SSH-USER SSH-HOST AWS-REGION IOT-THING-NAME"
  exit 3
fi

AWS_PROFILE=$1
USER=$2
HOST=$3
AWS_REGION=$4
IOT_THING_NAME=$5

HOST_STRING="${USER}@${HOST}"

echo "\n===[ Installing prerequisites ]===\n"
ssh -t $HOST_STRING "sudo apt-get update && sudo apt-get install -y openjdk-8-jdk curl unzip"

echo "\n===[ Downloading Greengrass v2 ]===\n"
ssh -t $HOST_STRING "cd ~ && curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip > \\
  greengrass-nucleus-latest.zip && yes | unzip greengrass-nucleus-latest.zip -d GreengrassCore && \\
  rm greengrass-nucleus-latest.zip"

export AWS_ACCESS_KEY_ID=$(aws configure get $AWS_PROFILE.aws_access_key_id)
export AWS_SECRET_ACCESS_KEY=$(aws configure get $AWS_PROFILE.aws_secret_access_key)
#export AWS_SESSION_TOKEN=$(aws configure get $AWS_PROFILE.aws_session_token)

echo "\n===[ Installing and provisioning Greengrass v2 ]===\n"
ssh -t $HOST_STRING "AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \\
  sudo -E java -Droot='/greengrass/v2' -Dlog.store=FILE -jar ./GreengrassCore/lib/Greengrass.jar \\
  --aws-region ${AWS_REGION} --thing-name ${IOT_THING_NAME} --thing-group-name GreengrassEdgeManagerGroup \\
  --tes-role-name MyGreengrassV2TokenExchangeRole --tes-role-alias-name MyGreengrassCoreTokenExchangeRoleAlias \\
  --component-default-user root:root --provision true --setup-system-service true --deploy-dev-tools true"

echo "\n===[ Greengrass v2 started ]===\n"

echo "\n===[ Adding S3 read permissions to TES role ]===\n"

aws iam attach-role-policy --profile $AWS_PROFILE --role-name MyGreengrassV2TokenExchangeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

echo "\n===[ Complete ]===\n"
