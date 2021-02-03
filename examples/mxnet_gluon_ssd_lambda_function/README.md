# Python SageMaker Edge Manager Agent + Greengrass V2 Example

## Create a model
Follow the sagemaker_edge_example.ipynb to create and compile a sample model for the edge device. In this example, we will use "jetson_xavier" as a target device.

## Install prerequisites
```console
~$ pip install grpcio-tools opencv-python
~$ pip install --upgrade protobuf
```

## Generate Python stubs
```console
~$ python -m grpc_tools.protoc -I=. --python_out=../examples/python_agent_example --grpc_python_out=../examples/python_agent_example ./agent.proto
```

## Write business/inference logic in the greengrass_lambda function.
1. Package this as a lambda function and upload it to AWS Console > AWS Lambda 
2. Choose Runtime as Python 3.7
3. Click on Deploy
4. Click on Actions > Publish new version.

## Now you are ready to deploy this function as a Greengrass v2 Component.
1. Goto AWS IoT Greengrass Console.
2. This step assumes a Greengrass Core device has already been created and we are deploying to that Greengrass Core.
3. Goto Greengrass > Components > Create component
4. Import from Lambda function
5. Choose the lamnbda function and version that you created earlier. You can run it as Greengrass container(explicit access to devices needs to be given) or No container mode(has access to devices implicitly)
6. Add dependency > aws.sagemaker.edgeManager(Component) > >=0.1.0(Version)
7. Create component

## Create a deployment to the core device with the following components
1. Machine Learning model. Refer to greengrass-v2/components/recipes/com.com.model.mxnet_gluoncv_ssd-0.1.0.yaml
2. Sagemaker Edge Manager Agent. Refer to greengrass-v2/components/recipes/aws.sagemaker.edgeManager-0.1.0.yaml
3. Lambda function Component. Refer to the section above.