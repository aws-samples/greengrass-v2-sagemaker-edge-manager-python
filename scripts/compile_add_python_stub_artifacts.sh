if [ $# -ne 3 ]; then
  echo 1>&2 "Usage: $0 PLATFORM COMPONENT-NAME COMPONENT-VERSION"
  exit 3
fi

PLATFORM=$1
COMPONENT=$2
VERSION=$3

python -m grpc_tools.protoc -I=$PLATFORM/edge-manager-package/docs/api/ \
  --python_out=components/artifacts/$COMPONENT/$VERSION \
  --grpc_python_out=components/artifacts/$COMPONENT/$VERSION agent.proto