#
# Copyright 2010-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
import grpc
import cv2
import numpy as np
import agent_pb2_grpc
from agent_pb2 import (ListModelsRequest, LoadModelRequest, PredictRequest,
                       UnLoadModelRequest, DescribeModelRequest, Tensor, TensorMetadata)
import logging
import sys
from threading import Timer
import platform
import os
import re
import subprocess
import traceback
import time
import random

#use USB Camera 1
cap = cv2.VideoCapture(1,cv2.CAP_V4L)
#use video file
#cap = cv2.VideoCapture("<ENTER_PATH_TO_VIDEO_FILE>")

# Setup logging to stdout
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

#set up Model parameters
#model_url = '/greengrass/v2/work/com.model.darknet/'
model_url = '/greengrass/v2/work/com.model.mxnet_gluoncv_ssd/'
#model_name = 'demo-darknet'
model_name = 'demo-ssd-new'
tensor_name = 'data'
#tensor_shape = [1, 3, 416, 416]
tensor_shape = [1, 3, 512, 512]
input_size = 512
object_categories = ['aeroplane', 'bicycle', 'bird', 'boat', 'bottle', 'bus', 'car', 'cat', 
                     'chair', 'cow', 'diningtable', 'dog', 'horse', 'motorbike', 'person', 
                     'pottedplant', 'sheep', 'sofa', 'train', 'tvmonitor']
#img_url = '/greengrass-ml/images/darknet_original.bmp'

# Mean and Std deviation of the RGB colors (collected from Imagenet dataset)
mean=[123.68,116.779,103.939]
std=[58.393,57.12,57.375]

#Need to wait for sagemaker.edge.agent to start serving requests
print("sleeping for sometime before loading")
#time.sleep(30)
print("Waking up")

#Create a channel
channel = grpc.insecure_channel('unix:///tmp/sagemaker_edge_agent_example.sock')
print('getting stubs!')
edge_manager_client = agent_pb2_grpc.AgentStub(channel)

print('calling LoadModel!')
try:
    response = edge_manager_client.LoadModel(
        LoadModelRequest(url=model_url, name=model_name))
except Exception as e:
    print(e)
    print('model already loaded!')

print('calling ListModels!')
response = edge_manager_client.ListModels(ListModelsRequest())

print('calling DescribeModel')
response = edge_manager_client.DescribeModel(
    DescribeModelRequest(name=model_name))

def greengrass_hello_world_run():
    global edge_manager_client        
    print('running now!')
    try:
        if not cap.isOpened():
            print("Cannot open camera\n")
            exit(1)
            
        ret, img = cap.read()
        #if reading from file
        #img = cv2.imread(img_url)
        
        print('calling PredictRequest on images !')
        #resize input before serving
        frame = resize_short_within(img, short=512)
        nn_input_size = input_size
        nn_input=cv2.resize(frame, (nn_input_size,int(nn_input_size/4*3)))
        nn_input=cv2.copyMakeBorder(nn_input,int(nn_input_size/8),int(nn_input_size/8),
                                0,0,cv2.BORDER_CONSTANT,value=(0,0,0))
        copy_frame = nn_input[:]                                        
        nn_input=nn_input.astype('float32')
        nn_input=nn_input.reshape((nn_input_size*nn_input_size ,3))
        scaled_frame=np.transpose(nn_input)
        scaled_frame[0,:] = scaled_frame[0,:]-mean[0]
        scaled_frame[0,:] = scaled_frame[0,:]/std[0]
        scaled_frame[1,:] = scaled_frame[1,:]-mean[1]
        scaled_frame[1,:] = scaled_frame[1,:]/std[1]
        scaled_frame[2,:] = scaled_frame[2,:]-mean[2]
        scaled_frame[2,:] = scaled_frame[2,:]/std[2]
        print("SHAPE:" + str(img.shape))

        request = PredictRequest(name=model_name, 
            tensors=[Tensor(tensor_metadata=TensorMetadata(
            name=tensor_name, data_type=5, shape=tensor_shape), byte_data=scaled_frame.tobytes())])

        print("Calling Predict on the Image...")
        response = edge_manager_client.Predict(request)
        
        #read output tensors
        i = 0
        output_detections = []
        
        for t in response.tensors:
            print("Flattened RAW Output Tensor : " + str(i+1))
            i += 1 
            deserialized_bytes = np.frombuffer(t.byte_data, dtype=np.float32)
            output_detections.append(np.asarray(deserialized_bytes))
            
        print(output_detections)
        #convert the bounding boxes 
        new_list = []
        for index,item in enumerate(output_detections[2]):
            if index % 4 == 0:
                new_list.append(output_detections[2][index-4:index])
        output_detections[2] = new_list[1:]
        #write to an input image
        visualize_detection(copy_frame, output_detections, classes=object_categories, thresh=0.2) 

        #save outputs
        save_path = os.path.join(os.getcwd(), "./", "output.jpg")
        cv2.imwrite(save_path, copy_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    except Exception as e:
        traceback.print_exc() 
        channel.close()
        logger.error("Failed to Run: " + repr(e))

    # Asynchronously schedule this function to be run again in X seconds
    Timer(2, greengrass_hello_world_run).start()


def visualize_detection(img, dets, classes=[], thresh=0.):
        """
        visualize detections in one image
        Parameters:
        ----------
        img : numpy.array
            image
        dets : numpy.array
            ssd detections
            each row is one object
        classes : tuple or list of str
            class names
        thresh : float
            score threshold
        """
        COLORS = np.random.uniform(0, 255, size=(len(classes), 3))
        
        colors = dict()
        klasses = dets[0]
        scores = dets[1]
        bbox = dets[2]
        for i in range(len(dets)):
            klass = klasses[i]
            score = scores[i]
            print(bbox[i])
            x0, y0, x1, y1 = bbox[i]
            if score < thresh:
                continue
            cls_id = int(klass)
            if cls_id not in colors:
                colors[cls_id] = (random.random(), random.random(), random.random())

            xmin, ymin, xmax, ymax = int(x0), int(y0), int(x1), int(y1)
            if classes and len(classes) > cls_id:
                class_name = classes[cls_id]
            # display the prediction
            label = "{}: {:.2f}%".format(classes[cls_id], score * 100)
            print("[INFO] {}".format(label))
            cv2.rectangle(img, (xmin, ymin),
                (xmax, ymax),
                COLORS[cls_id], 2)
            y = ymin - 15 if ymin - 15 > 15 else ymin + 15
            cv2.putText(img, label, (xmin, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[cls_id], 2)


def _get_interp_method(interp, sizes=()):
    """Get the interpolation method for resize functions.
    The major purpose of this function is to wrap a random interp method selection
    and a auto-estimation method.

    Parameters
    ----------
    interp : int
        interpolation method for all resizing operations

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
    return interp


def resize_short_within(img, short=512, max_size=1024, mult_base=32, interp=2):
    """
    resizes the short side of the image so the aspect ratio remains the same AND the short
    side matches the convolutional layer for the network

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

# Start executing the function above
greengrass_hello_world_run()

# This is a dummy handler and will not be invoked
# Instead the code above will be executed in an infinite loop for our example
def function_handler(event, context):
    return
