#
# Copyright 2010-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
import cv2
import numpy as np
import random
import argparse
import time
import json
import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.model import (
    QOS,
    PublishToIoTCoreRequest
)
import math
import agent_pb2_grpc
import grpc
from agent_pb2 import (ListModelsRequest, LoadModelRequest, PredictRequest,
                       UnLoadModelRequest, DescribeModelRequest, CaptureDataRequest, Tensor, 
                       TensorMetadata, Timestamp)
import signal
import sys
import uuid

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--stream', action='store', type=str, required=True, dest='stream_path', help='RTSP Stream URL')
parser.add_argument('-c', '--model-component', action='store', type=str, required=True, dest='model_component_name', help='Name of the GGv2 component containing the model')
parser.add_argument('-m', '--model-name', action='store', type=str, required=True, dest='model_name', help='Friendly name of the model from Edge Packaging Job')
parser.add_argument('-q', '--quantized', action='store', type=str, required=True, dest='quant', help='Is the model quantized?')
parser.add_argument('-a', '--capture', action='store', type=str, required=True, dest='capture_data', default=False, help='Capture inference metadata and raw output')

args = parser.parse_args()

stream_path = args.stream_path
model_component_name = args.model_component_name
model_name = args.model_name
quant = args.quant == 'True'
capture_inference = args.capture_data == 'True'

print ('RTSP stream is at ' + stream_path)
print ('Model Greengrass v2 component name is ' + model_component_name)
print ('Model name is ' + model_name)
print ('Model is quantized: ' + str(quant))

model_url = '/greengrass/v2/work/' + model_component_name
tensor_name = 'input'
SIZE = 224
tensor_shape = [1, SIZE, SIZE, 3]

inference_result_topic = "em/inference"
ipc_client = awsiot.greengrasscoreipc.connect()

channel = grpc.insecure_channel('unix:///tmp/sagemaker_edge_agent_example.sock')
edge_manager_client = agent_pb2_grpc.AgentStub(channel)

# When the component is stopped.
def sigterm_handler(signum, frame):
    global edge_manager_client
    try:
        response = edge_manager_client.UnLoadModel(UnLoadModelRequest(name=model_name))
        print ('Model unloaded.')
        sys.exit(0)
    except Exception as e:
        print ('Model failed to unload')
        print (e)
        sys.exit(-1)

signal.signal(signal.SIGINT, sigterm_handler)
signal.signal(signal.SIGTERM, sigterm_handler)

def preprocess_frame(captured_frame):

    if not quant:
        frame = resize_short_within(captured_frame, short=SIZE, max_size=SIZE * 2)
        scaled_frame = cv2.resize(frame, (SIZE, int(SIZE/4 * 3 )))
        scaled_frame = cv2.copyMakeBorder(scaled_frame, int(SIZE / 8), int(SIZE / 8),
                                    0, 0, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        scaled_frame = np.asarray(scaled_frame)
        # normalization according to https://github.com/tensorflow/tensorflow/blob/a4dfb8d1a71385bd6d122e4f27f86dcebb96712d/tensorflow/python/keras/applications/imagenet_utils.py#L259
        scaled_frame = (scaled_frame/127.5).astype(np.float32)
        scaled_frame -= 1.
        return scaled_frame
    
    else:
        scaled_frame = cv2.resize(captured_frame, (SIZE,SIZE))
        return scaled_frame

def build_message(detections, performance, model_name):
    if not quant:
        index = np.argmax(detections[0])
        confidence = detections[0][index]
    else:
        index = np.argmax(detections)
        confidence = (detections[0][index]/255)

    return {
        "index" : str(index-1),
        "confidence" : str(confidence),
        "performance" : str(performance),
        "model_name" : model_name
    }

# read output tensors and append them to matrix
def process_output_tensor(response):

    detections = []
    for t in response.tensors:
        deserialized_bytes = np.frombuffer(t.byte_data, dtype=np.uint8)
        detections.append(np.asarray(deserialized_bytes))
    
    return (detections)

# IPC publish to IoT Core
def publish_results_to_iot_core (message):
    # Publish highest confidence result to AWS IoT Core
    global ipc_client
    request = PublishToIoTCoreRequest()
    request.topic_name = inference_result_topic
    request.payload = bytes(json.dumps(message), "utf-8")
    request.qos = QOS.AT_LEAST_ONCE
    operation = ipc_client.new_publish_to_iot_core()
    operation.activate(request)
    future = operation.get_response()
    future.result(10)

def run():
    global edge_manager_client
    try:
        cap = cv2.VideoCapture(stream_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        ret, captured_frame = cap.read()
    except Exception as e:
        print('Stream failed to open.')
        cap.release()
        print(e)
        exit (-1)

    try:
        response = edge_manager_client.LoadModel(
            LoadModelRequest(url=model_url, name=model_name))
    except Exception as e:
        print('Model failed to load.')
        print(e)

    while (cap.isOpened() and ret):

        frameId = cap.get(1)
        ret, frame = cap.read()

        #perform inference once per second
        if (frameId % math.floor(fps) == 0 ):
            img = preprocess_frame(frame)
            
            try:
                before = time.time()
                request = PredictRequest(name=model_name, tensors=[Tensor(tensor_metadata=TensorMetadata(
                    name=tensor_name, data_type=5, shape=tensor_shape), byte_data=img.tobytes())])
                response = edge_manager_client.Predict(request)
                after = time.time()
                performance = ((after)-(before))*1000
                detections = process_output_tensor(response)
                message = build_message(detections, performance, model_name)
                publish_results_to_iot_core (message)

            except Exception as e:
                print('Prediction failed')
                print(e)

            if capture_inference:
                print ('Capturing inference data in Amazon S3')
                now = time.time()
                seconds = int(now)
                nanos = int((now - seconds) * 10**9)
                timestamp = Timestamp(seconds=seconds, nanos=nanos)
                request = CaptureDataRequest(
                    model_name=model_name,
                    capture_id=str(uuid.uuid4()),
                    inference_timestamp=timestamp,
                    input_tensors=[Tensor(tensor_metadata=TensorMetadata(name="input", data_type=5, shape=tensor_shape), 
                        byte_data=img.tobytes())],
                    output_tensors=[Tensor(tensor_metadata=TensorMetadata(name="output", data_type=5, shape=[1,257]), 
                        byte_data=detections[0].tobytes())]
                )
                try:
                    response = edge_manager_client.CaptureData(request)
                except Exception as e:
                    print('CaptureData request failed')
                    print(e)


## Scaling functions
def _get_interp_method(interp, sizes=()):
    """Get the interpolation method for resize functions.
    The major purpose of this function is to wrap a random interp method selection
    and a auto-estimation method.
​
    Parameters
    ----------
    interp : int
        interpolation method for all resizing operations
​
        Possible values:
        0: Nearest Neighbors Interpolation.
        1: Bilinear interpolation.
        2: Area-based (resampling using pixel area relation). It may be a
        preferred method for image decimation, as it gives moire-free
        results. But when the image is zoomed, it is similar to the Nearest
        Neighbors method. (used by default).
        3: Bicubic interpolation over 4x4 pixel neighborhood.
        4: Lanczos interpolation over 8x8 pixel neighborhood.
        9: Cubic for enlarge, area for shrink, bilinear for others
        10: Random select from interpolation method metioned above.
        Note:
        When shrinking an image, it will generally look best with AREA-based
        interpolation, whereas, when enlarging an image, it will generally look best
        with Bicubic (slow) or Bilinear (faster but still looks OK).
        More details can be found in the documentation of OpenCV, please refer to
        http://docs.opencv.org/master/da/d54/group__imgproc__transform.html.
    sizes : tuple of int
        (old_height, old_width, new_height, new_width), if None provided, auto(9)
        will return Area(2) anyway.
​
    Returns
    -------
    int
        interp method from 0 to 4
    """
    if interp == 9:
        if sizes:
            assert len(sizes) == 4
            oh, ow, nh, nw = sizes
            if nh > oh and nw > ow:
                return 2
            elif nh < oh and nw < ow:
                return 3
            else:
                return 1
        else:
            return 2
    if interp == 10:
        return random.randint(0, 4)
    if interp not in (0, 1, 2, 3, 4):
        raise ValueError('Unknown interp method %d' % interp)


def resize_short_within(img, short=512, max_size=1024, mult_base=32, interp=2):
    """
    resizes the short side of the image so the aspect ratio remains the same AND the short
    side matches the convolutional layer for the network
​
    Args:
    -----
    img: np.array
        image you want to resize
    short: int
        the size to reshape the image to
    max_size: int
        the max size of the short side
    mult_base: int
        the size scale to readjust the resizer
    interp: int
        see '_get_interp_method'
    Returns:
    --------
    img: np.array
        the resized array
    """
    h, w, _ = img.shape
    im_size_min, im_size_max = (h, w) if w > h else (w, h)
    scale = float(short) / float(im_size_min)
    if np.round(scale * im_size_max / mult_base) * mult_base > max_size:
        # fit in max_size
        scale = float(np.floor(max_size / mult_base) * mult_base) / float(im_size_max)
    new_w, new_h = (
        int(np.round(w * scale / mult_base) * mult_base),
        int(np.round(h * scale / mult_base) * mult_base)
    )
    img = cv2.resize(img, (new_w, new_h),
                     interpolation=_get_interp_method(interp, (h, w, new_h, new_w)))
    return img


if __name__ == '__main__':
    run()