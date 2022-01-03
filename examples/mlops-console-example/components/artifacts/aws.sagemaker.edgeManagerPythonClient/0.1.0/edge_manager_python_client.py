#
# Copyright 2010-2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
import agent_pb2_grpc
import cv2
from agent_pb2 import (ListModelsRequest, LoadModelRequest, PredictRequest,
                       UnLoadModelRequest, DescribeModelRequest, CaptureDataRequest, Tensor, 
                       TensorMetadata, Timestamp)
import grpc
import numpy as np
import random
import uuid
import argparse
import time
import signal
import sys
import json
import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.model import (
    QOS,
    PublishToIoTCoreRequest
)

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--image-path', action='store', type=str, required=True, dest='image_path', help='Path to Sample Images')
parser.add_argument('-c', '--model-component', action='store', type=str, required=True, dest='model_component_name', help='Name of the GGv2 component containing the model')
parser.add_argument('-m', '--model-name', action='store', type=str, required=True, dest='model_name', help='Friendly name of the model from Edge Packaging Job')
parser.add_argument('-a', '--capture', action='store', type=str, required=True, dest='capture_data', default=False, help='Capture inference metadata and raw output')

args = parser.parse_args()

image_path = args.image_path
model_component_name = args.model_component_name
model_name = args.model_name
capture_inference = args.capture_data == 'True'

print ('Images stored in ' + image_path)
print ('Model Greengrass v2 component name is ' + model_component_name)
print ('Model name is ' + model_name)
print ('Capture inference data is set to ' + str(capture_inference))

model_url = '/greengrass/v2/work/' + model_component_name
tensor_name = 'data'
SIZE = 224
tensor_shape = [1, 3, SIZE, SIZE]
image_urls = [image_path +'/rainbow.jpeg', image_path+'/tomato.jpeg', image_path+'/dog.jpeg', image_path+'/frog.jpeg']

channel = grpc.insecure_channel('unix:///tmp/sagemaker_edge_agent_example.sock')

inference_result_topic = "em/inference"
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

# classifications for the model
class_labels = ['ak47', 'american-flag', 'backpack', 'baseball-bat', 'baseball-glove', 'basketball-hoop', 'bat',
                'bathtub', 'bear', 'beer-mug', 'billiards', 'binoculars', 'birdbath', 'blimp', 'bonsai-101',
                'boom-box', 'bowling-ball', 'bowling-pin', 'boxing-glove', 'brain-101', 'breadmaker', 'buddha-101',
                'bulldozer', 'butterfly', 'cactus', 'cake', 'calculator', 'camel', 'cannon', 'canoe', 'car-tire',
                'cartman', 'cd', 'centipede', 'cereal-box', 'chandelier-101', 'chess-board', 'chimp', 'chopsticks',
                'cockroach', 'coffee-mug', 'coffin', 'coin', 'comet', 'computer-keyboard', 'computer-monitor',
                'computer-mouse', 'conch', 'cormorant', 'covered-wagon', 'cowboy-hat', 'crab-101', 'desk-globe',
                'diamond-ring', 'dice', 'dog', 'dolphin-101', 'doorknob', 'drinking-straw', 'duck', 'dumb-bell',
                'eiffel-tower', 'electric-guitar-101', 'elephant-101', 'elk', 'ewer-101', 'eyeglasses', 'fern',
                'fighter-jet', 'fire-extinguisher', 'fire-hydrant', 'fire-truck', 'fireworks', 'flashlight',
                'floppy-disk', 'football-helmet', 'french-horn', 'fried-egg', 'frisbee', 'frog', 'frying-pan',
                'galaxy', 'gas-pump', 'giraffe', 'goat', 'golden-gate-bridge', 'goldfish', 'golf-ball', 'goose',
                'gorilla', 'grand-piano-101', 'grapes', 'grasshopper', 'guitar-pick', 'hamburger', 'hammock',
                'harmonica', 'harp', 'harpsichord', 'hawksbill-101', 'head-phones', 'helicopter-101', 'hibiscus',
                'homer-simpson', 'horse', 'horseshoe-crab', 'hot-air-balloon', 'hot-dog', 'hot-tub', 'hourglass',
                'house-fly', 'human-skeleton', 'hummingbird', 'ibis-101', 'ice-cream-cone', 'iguana', 'ipod', 'iris',
                'jesus-christ', 'joy-stick', 'kangaroo-101', 'kayak', 'ketch-101', 'killer-whale', 'knife', 'ladder',
                'laptop-101', 'lathe', 'leopards-101', 'license-plate', 'lightbulb', 'light-house', 'lightning',
                'llama-101', 'mailbox', 'mandolin', 'mars', 'mattress', 'megaphone', 'menorah-101', 'microscope',
                'microwave', 'minaret', 'minotaur', 'motorbikes-101', 'mountain-bike', 'mushroom', 'mussels',
                'necktie', 'octopus', 'ostrich', 'owl', 'palm-pilot', 'palm-tree', 'paperclip', 'paper-shredder',
                'pci-card', 'penguin', 'people', 'pez-dispenser', 'photocopier', 'picnic-table', 'playing-card',
                'porcupine', 'pram', 'praying-mantis', 'pyramid', 'raccoon', 'radio-telescope', 'rainbow', 'refrigerator',
                'revolver-101', 'rifle', 'rotary-phone', 'roulette-wheel', 'saddle', 'saturn', 'school-bus',
                'scorpion-101', 'screwdriver', 'segway', 'self-propelled-lawn-mower', 'sextant', 'sheet-music', 
                'skateboard', 'skunk', 'skyscraper', 'smokestack', 'snail', 'snake', 'sneaker', 'snowmobile',
                'soccer-ball', 'socks', 'soda-can', 'spaghetti', 'speed-boat', 'spider', 'spoon', 'stained-glass',
                'starfish-101', 'steering-wheel', 'stirrups', 'sunflower-101', 'superman', 'sushi', 'swan',
                'swiss-army-knife', 'sword', 'syringe', 'tambourine', 'teapot', 'teddy-bear', 'teepee',
                'telephone-box', 'tennis-ball', 'tennis-court', 'tennis-racket', 'theodolite', 'toaster', 'tomato',
                'tombstone', 'top-hat', 'touring-bike', 'tower-pisa', 'traffic-light', 'treadmill', 'triceratops',
                'tricycle', 'trilobite-101', 'tripod', 't-shirt', 'tuning-fork', 'tweezer', 'umbrella-101', 'unicorn',
                'vcr', 'video-projector', 'washing-machine', 'watch-101', 'waterfall', 'watermelon', 'welding-mask',
                'wheelbarrow', 'windmill', 'wine-bottle', 'xylophone', 'yarmulke', 'yo-yo', 'zebra', 'airplanes-101',
                'car-side-101', 'faces-easy-101', 'greyhound', 'tennis-shoes', 'toad', 'clutter']

def run():
    global edge_manager_client
    ipc_client = awsiot.greengrasscoreipc.connect()

    try:
        response = edge_manager_client.LoadModel(
            LoadModelRequest(url=model_url, name=model_name))
    except Exception as e:
        print('Model failed to load.')
        print(e)

    while (True):
        time.sleep(30)
        print('New prediction')

        image_url = image_urls[random.randint(0,3)]
        print ('Picked ' + image_url + ' to perform inference on')

        # Scale image / preprocess
        img = cv2.imread(image_url)
        frame = resize_short_within(img, short=SIZE, max_size=SIZE * 2)
        nn_input_size = SIZE
        nn_input = cv2.resize(frame, (nn_input_size, int(nn_input_size/4 * 3 )))
        nn_input = cv2.copyMakeBorder(nn_input, int(nn_input_size / 8), int(nn_input_size / 8),
                                    0, 0, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        copy_frame = nn_input[:]
        nn_input = nn_input.astype('float32')
        nn_input = nn_input.reshape((nn_input_size * nn_input_size, 3))
        scaled_frame = np.transpose(nn_input)

        # Call prediction
        request = PredictRequest(name=model_name, tensors=[Tensor(tensor_metadata=TensorMetadata(
            name=tensor_name, data_type=5, shape=tensor_shape), byte_data=scaled_frame.tobytes())])
        
        try:
            response = edge_manager_client.Predict(request)
        except Exception as e:
            print('Prediction failed')
            print(e)

        # read output tensors and append them to matrix
        detections = []
        for t in response.tensors:
            deserialized_bytes = np.frombuffer(t.byte_data, dtype=np.float32)
            detections.append(np.asarray(deserialized_bytes))

        # Get the highest confidence inference result
        index = np.argmax(detections[0])
        result = class_labels[index]
        confidence = detections[0][index]

        # Print results in local log
        print('Result is ', result)
        print('Confidence is ', confidence)

        # Publish highest confidence result to AWS IoT Core
        print ('Got inference results, publishing to AWS IoT Core')
        message = {
            "result" : result,
            "confidence" : str(confidence)
        }
        request = PublishToIoTCoreRequest()
        request.topic_name = inference_result_topic
        request.payload = bytes(json.dumps(message), "utf-8")
        request.qos = QOS.AT_LEAST_ONCE
        operation = ipc_client.new_publish_to_iot_core()
        operation.activate(request)
        future = operation.get_response()
        future.result(10)

        # capture inference results in S3 if enabled
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
                    byte_data=scaled_frame.tobytes())],
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