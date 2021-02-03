if [ $# -ne 4 ]; then
  echo 1>&2 "Usage: $0 AWS-PROFILE PLATFORM EDGE-MANAGER-COMPONENT-VERSION REGION"
  exit 3
fi

AWS_PROFILE=$1
PLATFORM=$2
VERSION=$3
AWS_REGION=$4

cp ./$PLATFORM/edge-manager-package/bin/sagemaker_edge_agent_binary ./components/artifacts/aws.sagemaker.edgeManager/$VERSION/

aws s3 cp s3://sagemaker-edge-release-store-us-west-2-linux-x64/Certificates/$AWS_REGION/$AWS_REGION.pem ./components/artifacts/aws.sagemaker.edgeManager/$VERSION/ --profile $AWS_PROFILE