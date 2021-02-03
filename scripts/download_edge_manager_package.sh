if [ $# -ne 2 ]; then
  echo 1>&2 "Usage: $0 AWS-PROFILE-NAME PLATFORM"
  exit 3
fi

AWS_PROFILE=$1
PLATFORM=$2

export VERSION=$(aws s3 ls s3://sagemaker-edge-release-store-us-west-2-$PLATFORM/Releases/ --profile $AWS_PROFILE | sort -r | sed -n 2p | xargs | cut -d' ' -f2 | cut -d'/' -f1)
mkdir -p $PLATFORM/edge-manager-package
aws s3 cp s3://sagemaker-edge-release-store-us-west-2-$PLATFORM/Releases/$VERSION/$VERSION.tgz ./$PLATFORM --profile $AWS_PROFILE
aws s3 cp s3://sagemaker-edge-release-store-us-west-2-$PLATFORM/Releases/$VERSION/sha256_hex.shasum ./$PLATFORM --profile $AWS_PROFILE
tar zxvf $PLATFORM/$VERSION.tgz -C $PLATFORM/edge-manager-package