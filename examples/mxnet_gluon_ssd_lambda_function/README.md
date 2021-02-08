# Python SageMaker Edge Manager Agent + Greengrass V2 Example
This example uses boto3 APIs to create a model that we can deploy to an edge device. For deployment of artifacts using Greengrass V2, this will walk you through the steps that you can follow in the AWS Console. If you want to use AWSCLI instead, please follow this https://github.com/aws-samples/greengrass-v2-sagemaker-edge-manager-python/blob/main/README.md. 

## Pre-Requisites
To run this example end to end, you will need an edge device (NVIDIA Jetson TX2/Xavier) that has internet connectivity. To start with, clone this repo and open sagemaker_edge_example.ipynb on either Sagemaker Studio instance or on Classic Jupyter Notebook instance in Sagemaker. 

## Model and Agent Artifacts
Follow the sagemaker_edge_example.ipynb to create and compile a sample model for the edge device. In this example, we will use "jetson_xavier" as a target device. This notebook shows how you can use a pretrained darknet(object detection) or pretrained keras(image classification) model. If you want to experiment with gluoncv_ssd_mobilenet model, use this Jupyter notebook - https://github.com/aws/amazon-sagemaker-examples/blob/master/sagemaker_neo_compilation_jobs/gluoncv_ssd_mobilenet/gluoncv_ssd_mobilenet_neo.ipynb

## Greengrass V2 Lambda function Component

### Write business/inference logic in the greengrass_lambda function.
1. See greengrass_lambda.py for example. Package this as a lambda function and upload it to AWS Console > AWS Lambda > Create Function
2. Choose Runtime as Python 3.7
3. Click on Deploy
4. Click on Actions > Publish new version.

### Now you are ready to deploy this function as a Greengrass v2 Component.
1. Goto AWS IoT Greengrass Console.
2. This step assumes a Greengrass Core device has already been created and we are deploying to that Greengrass Core.
3. Goto Greengrass > Components > Create component
4. Import from Lambda function
5. Choose the lambda function and version that you created earlier. You can run it as Greengrass container(requires explicit access to devices) or in No container mode(has access to devices connected to the core)
6. Add dependency : aws.sagemaker.edgeManager(Component) > >=0.1.0(Version)
7. Create component

### Update your Greengrass v2 deployment to include all the required components

- com.model.darknet v0.1.0
- com.model.mxnet_gluoncv_ssd v0.1.0
- aws.sagemaker.edgeManager v0.1.0
- greengrass_lambda v0.1.0

