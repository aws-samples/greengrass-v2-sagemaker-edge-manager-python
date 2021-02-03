import grpc
import sys
import cv2
import numpy as np
import random
import agent_pb2_grpc
from agent_pb2 import (ListModelsRequest, LoadModelRequest, PredictRequest,
                       UnLoadModelRequest, DescribeModelRequest, Tensor, TensorMetadata)

model_url = '../com.model.darknet'
model_name = 'darknet-model'
tensor_name = 'data'
SIZE = 416
tensor_shape = [1, 3, SIZE, SIZE]
image_url = sys.argv[1]

print('IMAGE URL IS {}'.format(image_url))

def run():
    with grpc.insecure_channel('unix:///tmp/sagemaker_edge_agent_example.sock') as channel:

        edge_manager_client = agent_pb2_grpc.AgentStub(channel)

        try:
            response = edge_manager_client.LoadModel(
                LoadModelRequest(url=model_url, name=model_name))
        except Exception as e:
            print(e)
            print('Model already loaded!')

        response = edge_manager_client.ListModels(ListModelsRequest())

        response = edge_manager_client.DescribeModel(
            DescribeModelRequest(name=model_name))

        # Mean and Std deviation of the RGB colors (collected from Imagenet dataset)
        mean = [123.68, 116.779, 103.939]
        std = [58.393, 57.12, 57.375]

        img = cv2.imread(image_url)
        frame = resize_short_within(img, short=SIZE, max_size=SIZE*2)
        nn_input_size = SIZE
        nn_input = cv2.resize(frame, (nn_input_size, int(nn_input_size / 4 * 3)))
        nn_input = cv2.copyMakeBorder(nn_input, int(nn_input_size / 8), int(nn_input_size / 8),
                                      0, 0, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        copy_frame = nn_input[:]
        nn_input = nn_input.astype('float32')
        nn_input = nn_input.reshape((nn_input_size * nn_input_size, 3))
        scaled_frame = np.transpose(nn_input)
        scaled_frame[0, :] = scaled_frame[0, :] - mean[0]
        scaled_frame[0, :] = scaled_frame[0, :] / std[0]
        scaled_frame[1, :] = scaled_frame[1, :] - mean[1]
        scaled_frame[1, :] = scaled_frame[1, :] / std[1]
        scaled_frame[2, :] = scaled_frame[2, :] - mean[2]
        scaled_frame[2, :] = scaled_frame[2, :] / std[2]

        request = PredictRequest(name=model_name, tensors=[Tensor(tensor_metadata=TensorMetadata(
            name=tensor_name, data_type=5, shape=tensor_shape), byte_data=scaled_frame.tobytes())])

        response = edge_manager_client.Predict(request)

        # read output tensors
        i = 0
        test_detections = []

        for t in response.tensors:
            print("Flattened RAW Output Tensor : " + str(i + 1))
            i += 1
            deserialized_bytes = np.frombuffer(t.byte_data, dtype=np.float32)
            test_detections.append(np.asarray(deserialized_bytes))

        print(test_detections)
        # convert the bounding boxes
        new_list = []
        for index, item in enumerate(test_detections[2]):
            if index % 4 == 0:
                new_list.append(test_detections[2][index - 4:index])
        test_detections[2] = new_list[1:]

        # get objects, scores, bboxes
        objects = test_detections[0]
        scores = test_detections[1]
        bounding_boxes = new_list[1:]

        print(objects)
        print(scores)
        print(bounding_boxes)

        response = edge_manager_client.UnLoadModel(
            UnLoadModelRequest(name=model_name))


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
