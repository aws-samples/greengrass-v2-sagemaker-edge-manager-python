## greengrass-v2-sagemaker-edge-manager-python

This code sample demonstrates how to integrate SageMaker Edge Manager with Greengrass v2 via components. At the end of the sample, you will have a Python-based component running inference at the edge with the SageMaker Edge Manager binary agent, and a YOLOv3 Darknet model.

### AWS CLI setup

Ensure you have AWS CLI installed, a IAM user with an access key, and a named profile configured:

* [Installing, updating, and uninstalling the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
* [Configuration basics](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)
* [Named profiles](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html)

### Define key variables
> NOTE: In this demo, we are using a NVIDIA Xavier NX / AGX Xavier development kit. Please adjust PLATFORM as required for your device.
```console
export AWS_PROFILE=<PROFILE-NAME>
export AWS_REGION=<REGION>
export PLATFORM=linux-armv8
export SSH_USER=<USER>
export SSH_HOST=<IP_ADDRESS>
export IOT_THING_NAME=<THING_NAME>
export BUCKET_NAME=<BUCKET_NAME>
```

### Allow executions of scripts
```console
chmod +x ./scripts/*.sh
```

### Make S3 bucket for your custom components
```console
aws s3 mb s3://$BUCKET_NAME --profile $AWS_PROFILE --region $AWS_REGION
```

### Download/upload Darknet sample model
```console
./scripts/download_upload_sample_model.sh $AWS_PROFILE $BUCKET_NAME
```

### Create SageMaker Execution Role
```console
export SM_ROLE_NAME=smem-role
./scripts/create_sagemaker_role.sh $AWS_PROFILE $SM_ROLE_NAME
```

### Compile model with SageMaker Neo
```console
./scripts/create_neo_compilation_job.sh $AWS_PROFILE $BUCKET_NAME $AWS_REGION $SM_ROLE_NAME
```

### Package Neo model in SageMaker Edge Manager
```console
./scripts/package_neo_model.sh $AWS_PROFILE $BUCKET_NAME $AWS_REGION $SM_ROLE_NAME
```

### Download, install, provision, and start Greengrass v2
> NOTE: this is done over SSH to avoid installing AWS CLI and credentials directly on the device.
```console
./scripts/install-ggv2-ssh.sh $AWS_PROFILE $SSH_USER $SSH_HOST $AWS_REGION $IOT_THING_NAME
```

### Download SageMaker Edge Manager archive
```console
./scripts/download_edge_manager_package.sh $AWS_PROFILE $PLATFORM    
```

### Add SageMaker Edge Manager agent binary to artifacts
```console
./scripts/add_agent_artifact.sh $AWS_PROFILE $PLATFORM 0.1.0 $AWS_REGION
```

### Compile and add SageMaker Edge Manager Python client stubs to artifacts
```console
pip install grpcio-tools
pip install --upgrade protobuf
./scripts/compile_add_python_stub_artifacts.sh $PLATFORM aws.sagemaker.edgeManagerPythonClient 0.1.0
```

### Create device fleet in SageMaker Edge Manager, and add device to fleet
```console
./scripts/create_device_fleet_register_device.sh $AWS_PROFILE $AWS_REGION $BUCKET_NAME $IOT_THING_NAME
```

### Update recipes
* In all of the recipe files, replace **YOUR_BUCKET_NAME** with the value assigned to $BUCKET_NAME
* Run the following to get your AWS account number
```console
aws sts get-caller-identity --profile $AWS_PROFILE | jq -r '.Account'
```
* In components/recipe/aws.sagemaker.edgeManager-0.1.0.yaml, update the endpoint with your region and account number:
```yaml
endpoint: arn:aws:iot:<AWS_REGION>:<ACCOUNT_NUMBER>:rolealias/SageMakerEdge-ggv2-smem-fleet
```

* In components/recipe/aws.sagemaker.edgeManager-0.1.0.yaml, update the URI with your region:
```yaml
- URI: s3://YOUR_BUCKET_NAME/artifacts/aws.sagemaker.edgeManager/0.1.0/<AWS_REGION>.pem
```

### Upload your custom components to S3 bucket
```console
./scripts/upload_component_version.sh $AWS_PROFILE com.model.darknet 0.1.0 $BUCKET_NAME $AWS_REGION
./scripts/upload_component_version.sh $AWS_PROFILE aws.sagemaker.edgeManager 0.1.0 $BUCKET_NAME $AWS_REGION 
./scripts/upload_component_version.sh $AWS_PROFILE aws.sagemaker.edgeManagerPythonClient 0.1.0 $BUCKET_NAME $AWS_REGION
```

> NOTE: you cannot overwrite an existing component version. To upload a new version, you will need to update the version number in the artifact directory, the recipe file name, and the version numbers in the recipe file.
> As an alternative, you can also delete a specific component version. For this, use the following command:
```console
./delete_component.sh $AWS_PROFILE <COMPONENT-NAME> <COMPONENT-VERSION> $AWS_REGION
```

### Update your Greengrass v2 deployment

Create a new Greengrass v2 deployment, including the following components:
* com.model.darknet v0.1.0
* aws.sagemaker.edgeManager v0.1.0
* aws.sagemaker.edgeManagerPythonClient v0.1.0

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

