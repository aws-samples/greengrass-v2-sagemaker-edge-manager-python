if [ $# -ne 5 ]; then
  echo 1>&2 "Usage: $0 AWS-PROFILE-NAME COMPONENT_NAME COMPONENT_VERSION BUCKET_NAME AWS_REGION"
  exit 3
fi

AWS_PROFILE=$1
COMPONENT_NAME=$2
COMPONENT_VERSION=$3
S3_BUCKET_NAME=$4
AWS_REGION=$5

cd components/artifacts/$COMPONENT_NAME/$COMPONENT_VERSION

for FILE in *; do aws s3api put-object --profile $AWS_PROFILE --bucket $S3_BUCKET_NAME --key artifacts/$COMPONENT_NAME/$COMPONENT_VERSION/$FILE --body $FILE; done

cd ../../..

aws greengrassv2 create-component-version --profile $AWS_PROFILE --inline-recipe fileb://recipes/$COMPONENT_NAME-$COMPONENT_VERSION.yaml --region $AWS_REGION