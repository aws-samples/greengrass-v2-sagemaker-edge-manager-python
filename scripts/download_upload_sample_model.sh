if [ $# -ne 2 ]; then
  echo 1>&2 "Usage: $0 AWS-PROFILE-NAME S3-BUCKET"
  exit 3
fi

AWS_PROFILE=$1
BUCKET_NAME=$2

mkdir -p ./models

wget -O ./models/yolov3-tiny.cfg https://github.com/pjreddie/darknet/blob/master/cfg/yolov3-tiny.cfg?raw=true
wget -O ./models/yolov3-tiny.weights https://pjreddie.com/media/files/yolov3-tiny.weights

tar -czvf yolo3-tiny.tar.gz ./models/yolov3-tiny.cfg ./models/yolov3-tiny.weights
mv yolo3-tiny.tar.gz ./models
rm ./models/yolov3-tiny.cfg ./models/yolov3-tiny.weights

aws s3 cp ./models/yolo3-tiny.tar.gz s3://$BUCKET_NAME/models/yolo3-tiny.tar.gz --profile $AWS_PROFILE