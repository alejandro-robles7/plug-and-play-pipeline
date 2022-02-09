import boto3, sys, os, json
import random, string, re
import botocore
import uuid, shutil
import urllib.request


codeCommit = boto3.client('codecommit')
s3 = boto3.resource('s3')
lambdaClient = boto3.client('lambda')
ecr = boto3.client('ecr')

def lambda_handler(event, context):
  print(event)
  responseData = {'status': 'NONE', 'repoName': 'NONE'}
  if event['RequestType'] == 'Create':
    
    bucketName = event['ResourceProperties'].get('bucketName')
    keyPrefix = event['ResourceProperties'].get('keyPrefix')
    Region = event['ResourceProperties'].get('Region')

    randStr = uuid.uuid4().hex

    source_url = 'https://'+bucketName+'.s3-'+Region+'.amazonaws.com/'+keyPrefix+'/scripts/repoCode.zip'
    print(source_url)
    try:
      urllib.request.urlretrieve(source_url, '/tmp/repoCode.zip')
    except:
      raise
    localDirectory = '/tmp/unzip/'
    try:
      shutil.unpack_archive('/tmp/repoCode.zip', localDirectory , 'zip')
    except:
      e = sys.exc_info()[0]
      f = sys.exc_info()[1]
      g = sys.exc_info()[2]
      print("error (main error): "+str(e) + str(f) + str(g))

    fileDirectory = localDirectory + 'modelCode'
    repoType = 'modelCode'
    repoName = repoType+'-'+randStr
    repoDescription = 'This repository contains all the model code.'
    createRepo(event, context, repoName, repoDescription, repoType, responseData, bucketName, keyPrefix, fileDirectory)

    fileDirectory = localDirectory + 'stateMachineCode'
    repoType = 'stateMachineCode'
    repoName = repoType+'-'+randStr
    repoDescription = 'This repository contains the code to create the AWS Step-Functions.'
    createRepo(event, context, repoName, repoDescription, repoType, responseData, bucketName, keyPrefix, fileDirectory)

    responseData['status'] = 'CREATED'
    responseData['repoId'] = randStr
    sendResponse(event, context, "SUCCESS", responseData, event["LogicalResourceId"])
  elif event['RequestType'] == 'Delete':

    # Get a list of all images in the ECR repo
    try:
      response = ecr.list_images(
          repositoryName=event['ResourceProperties'].get('ecrModelRepo')
      )
    except:
      e = sys.exc_info()[0]
      f = sys.exc_info()[1]
      g = sys.exc_info()[2]
      print("error (list_images error): "+str(e) + str(f) + str(g))
    # Create an array of images to delete
    imageIds = []
    for image in response['imageIds']:
        print(image['imageDigest'])
        thisImage = { 'imageDigest': image['imageDigest'] }
        imageIds.append(thisImage)
    # Delete the images from the repo
    try:
      ecr.batch_delete_image(
          repositoryName=event['ResourceProperties'].get('ecrModelRepo'),
          imageIds=imageIds
      )
    except:
      e = sys.exc_info()[0]
      f = sys.exc_info()[1]
      g = sys.exc_info()[2]
      print("error (batch_delete_images error): "+str(e) + str(f) + str(g))

    try:
      # Delete the files in the data bucket and the ecr bucket
      s3.Bucket( event['ResourceProperties'].get('modelDataBucket') ).object_versions.all().delete()
      s3.Bucket( event['ResourceProperties'].get('modelArtifactBucket') ).object_versions.all().delete()
    except:
      sendResponse(event, context, "FAILED", responseData, event["LogicalResourceId"])
    try:
      s3.Bucket( event['ResourceProperties'].get('ecrBucket') ).object_versions.all().delete()
    except:
      sendResponse(event, context, "FAILED", responseData, event["LogicalResourceId"])

    repoName=os.environ['modelCode']
    try:
      response = codeCommit.delete_repository(repositoryName=repoName)
    except:
      sendResponse(event, context, "FAILED", responseData, event["LogicalResourceId"])
    repoName=os.environ['stateMachineCode']
    try:
      response = codeCommit.delete_repository(repositoryName=repoName)
    except:
      sendResponse(event, context, "FAILED", responseData, event["LogicalResourceId"])

    responseData['status'] = 'DELETED'
    sendResponse(event, context, "SUCCESS", responseData, event["LogicalResourceId"])

# This sends the data to CFN to signal success or fail. I am using this code instead of using cfn_response because
# Lambda is deprecating support for the requests module. This uses Curl instead.
def sendResponse(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False):
  # Setup Arrays to pass data to CloudFormation so it gets a success signal
  responseBody = {}
  responseBody['Status'] = responseStatus
  responseBody['Reason'] = 'Configuration Complete. See the details in CloudWatch Log Stream: ' + context.log_stream_name
  responseBody['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
  responseBody['StackId'] = event['StackId']
  responseBody['RequestId'] = event['RequestId']
  responseBody['LogicalResourceId'] = event['LogicalResourceId']
  responseBody['UniqueId'] = 'RequestPassed1' # Add auto-incrimenter to this if multiple counts
  responseBody['Data'] = responseData
  json_responseBody = json.dumps(responseBody)
  # print("Response body:\n" + json_responseBody)
  curlCMD = "curl -X PUT -H 'Content-Type:' --data-binary '" + json_responseBody + "' \"" + event["ResponseURL"] + "\""
  # print(curlCMD)
  try:
    os.system(curlCMD)
  except Exception as e:
    print('Error: ' + str(e))

def createRepo(event, context, repoName, repoDescription, repoType, responseData, bucketName, keyPrefix, fileDirectory):
  try:
    response = codeCommit.create_repository(
      repositoryName=repoName,
      repositoryDescription=repoDescription)
  except:
    e = sys.exc_info()[0]
    f = sys.exc_info()[1]
    g = sys.exc_info()[2]
    print("error (main error): "+str(e) + str(f) + str(g))
    responseData['Data'] = f"Exception raised for function: \nException details: \n{e}"
    sendResponse(event, context, "FAILED", responseData, event["LogicalResourceId"])
  try:
    envVars = {}
    # Get the current environmental variables so you don't overwrite any
    print(os.environ['AWS_LAMBDA_FUNCTION_NAME'])
    lambdaEnvVars = lambdaClient.get_function_configuration(FunctionName=os.environ['AWS_LAMBDA_FUNCTION_NAME'])
    try:
      lambdaEnvVars['Environment']['Variables']
    except:
      print("Variable not defined.")
    else:
      envVars = lambdaEnvVars['Environment']['Variables']
    envVars[repoType] = repoName
    # Update the environmental variables to use for deleting the repos
    lambdaResponse = lambdaClient.update_function_configuration(
      FunctionName=os.environ['AWS_LAMBDA_FUNCTION_NAME'],
      Environment={
        'Variables': envVars
      },
    )
  except:
    e = sys.exc_info()[0]
    print("error (update lambda function): "+str(e))
    responseData['Data'] = f"Exception raised for function: \nException details: \n{e}"
    sendResponse(event, context, "FAILED", responseData, event["LogicalResourceId"])

  # putFiles = createFileVariable(event, context, keyPrefix, fileDirectory, bucketName)
  putFiles = createFile(event, context, keyPrefix, fileDirectory)
  # Create an initial commit with files from above
  try:
    response = codeCommit.create_commit(repositoryName=repoName, branchName='main', commitMessage='Initial commit with sample files', putFiles=putFiles)
  except:
    print('adding commit failed')
    e = sys.exc_info()[0]
    f = sys.exc_info()[1]
    g = sys.exc_info()[2]
    print("error (main error): "+str(e) + str(f) + str(g))
    print('------')
    sendResponse(event, context, "FAILED", responseData, event["LogicalResourceId"])
  try:
    codeCommit.create_branch(repositoryName=repoName, branchName='main',  commitId=response['commitId'])
  except:
    print('Creating branch failed')
    sendResponse(event, context, "FAILED", responseData, event["LogicalResourceId"])

def createFile(event, context, keyPrefix, fileDirectory):
  print("::createFile::")
  print(fileDirectory)
  putFiles = []
  binFile = False
  print('All the files::::')
  for root, dirs, files in os.walk(fileDirectory):
    for filename in files:
      fullFileName = root+'/'+filename
      try:
        openFile = open(fullFileName, 'r')
      except:
        e = sys.exc_info()[0]
        f = sys.exc_info()[1]
        g = sys.exc_info()[2]
        print("error (open error): "+str(e) + str(f) + str(g))
      # Try to read the file contents
      try:
        fileContent = openFile.read()
      except: # If you get an error, its probably a binary file, so try that. Nasty hack.
        openFile = open(fullFileName, 'rb')
        fileContent = openFile.read()
        binFile = True
        e = sys.exc_info()[0]
        f = sys.exc_info()[1]
        g = sys.exc_info()[2]
        print("error (read error): "+str(e) + str(f) + str(g))
      if binFile:
        sendContent = fileContent
        binFile = False
      else:
        # Need to add some hardcoded values here for convenience at the moment
        # This needs to be made into variables to keep things easy 
        if filename == 'state_machine_manager.py':
          fileContent = fileContent.replace('[SageMakerRole]', event['ResourceProperties'].get('SageMakerRole'))
          fileContent = fileContent.replace('[StepFunctionsRole]', event['ResourceProperties'].get('StepFunctionsRole'))
          fileContent = fileContent.replace('[AccountId]', context.invoked_function_arn.split(":")[4])
          fileContent = fileContent.replace('[Region]', os.environ['AWS_REGION'])
          fileContent = fileContent.replace('[ecrModelRepo]', event['ResourceProperties'].get('ecrModelRepo'))
          fileContent = fileContent.replace('[trainingStateMachine]', event['ResourceProperties'].get('trainingStateMachine'))
          fileContent = fileContent.replace('[trainingStateMachineName]', event['ResourceProperties'].get('trainingStateMachineName'))
          fileContent = fileContent.replace('[dynamoDBTable]', event['ResourceProperties'].get('dynamoDBTable'))
          fileContent = fileContent.replace('[endpointWaitLambda]', event['ResourceProperties'].get('endpointWaitLambda'))
          fileContent = fileContent.replace('[modelTestLambda]', event['ResourceProperties'].get('modelTestLambda'))
          fileContent = fileContent.replace('[modelArtifactBucket]', event['ResourceProperties'].get('modelArtifactBucket'))
          fileContent = fileContent.replace('[kmsKey]', event['ResourceProperties'].get('kmsKey'))
        if filename == 'buildspec.yml':
          fileContent = fileContent.replace('[AccountId]', context.invoked_function_arn.split(":")[4])
          fileContent = fileContent.replace('[Region]', os.environ['AWS_REGION'])
          fileContent = fileContent.replace('[trainingStateMachine]', event['ResourceProperties'].get('trainingStateMachine'))
        sendContent = fileContent.encode()

      newFile = {
        'filePath': fullFileName.replace(fileDirectory, ''),
        'fileMode': 'NORMAL',
        'fileContent': sendContent
        }
      putFiles.append(newFile)
  print('All the files::::')

  return(putFiles)
