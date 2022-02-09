import json, boto3, os

def lambda_handler(event, context):
  s3 = boto3.resource('s3')
  responseData = {'status': 'NONE'}

  # If AWS CloudFormation triggers the function with CREATE, do the following
  if event['RequestType'] == 'Create':
    # Get variables from the event (populated by the AWS CloudFormation trigger)
    sourceBucket = event['ResourceProperties'].get('sourceBucket')
    keyPrefix = event['ResourceProperties'].get('keyPrefix')
    destinationBucket = event['ResourceProperties'].get('destinationBucket')

    # Designate what files need to be put in the Amazon S3 bucket
    fileList = [ 'smoketest/iris.csv', 'smoketest/output.csv', 'train/iris-2.csv', 'train/iris.csv', 'validation/iris.csv' ]
    for file in fileList:
      sourceKey = keyPrefix+'/scripts/data/'+file
      sourceObject = { 'Bucket': sourceBucket, 'Key': sourceKey }
      try:
        # Copy the files to the Amazon S3 bucket
        s3.meta.client.copy(sourceObject, destinationBucket, 'v1.0/'+file )
      except Exception as e:
        print(e)
        sendResponse(event, context, "FAILED", responseData, event["LogicalResourceId"]);
    responseData['status'] = 'CREATED'
    sendResponse(event, context, "SUCCESS", responseData, event["LogicalResourceId"]);
  # If AWS CloudFormation triggers the function with DELEVE, do the following
  elif event['RequestType'] == 'Delete':
    # THIS NEEDS TO BE WRITTEN TO DELETE FILES FORM DESTINATIONBUCKET!!!!
    responseData['status'] = 'DELETED'
    sendResponse(event, context, "SUCCESS", responseData, event["LogicalResourceId"]);

# This function sends the CFN response signal so that AWS CloudFormation knows that the function exited with success/fail
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
