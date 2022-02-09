import json, boto3, os, datetime, logging, sys, re
from decimal import Decimal
import pandas as pd
import numpy as np

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    # Dump the event for creating a test later
    logger.info(json.dumps(event))

    ecrArn = event['Input']['ecrArn']
    ecrTag = ecrArn.split(':')[1]
    logger.info("ECR Tag: " + ecrTag)

    # Get the s3 bucket name from the full path
    version = event['Input']['dataBucketPath'].split('/')[3]
    logger.info(version)
    suffix = '/'+version+'/train'
    logger.info(suffix)
    dataBucket = event['Input']['dataBucketPath'].split('/')[2]
    logger.info(dataBucket)

    # Set fixed locations to expect validation data to exist
    objectPath = version+'/validation/'
    fileName = 'iris.csv'

    logger.info(event['Input']['Endpoint'])
    endpointName = event['Input']['Endpoint']

    s3 = boto3.resource('s3')
    sagemaker = boto3.client('runtime.sagemaker')
    thisBucket = s3.Bucket(dataBucket)

    # Download the validation file to use for testing
    try:
      thisBucket.download_file(objectPath+fileName, '/tmp/'+fileName)
    except:
      e = sys.exc_info()[0]
      f = sys.exc_info()[1]
      g = sys.exc_info()[2]
      logger.error("error (update error): "+str(e) + str(f) + str(g))

    try:
      predictions = ""
      with open('/tmp/'+fileName, 'r') as file:
        for line in file:
          print('.', end='', flush=True)
          # Access the Amazon SageMaker endpoint to run tests
          response = sagemaker.invoke_endpoint(
            EndpointName=endpointName,
            Body=line.rstrip('\n'),
            ContentType='text/csv'
          )
          predictions = ','.join([predictions, response['Body'].read().decode('utf-8').rstrip('\n')])
        print('Done.')
    except:
        raise

    logger.info(predictions)

    target_labels = pd.read_csv('/tmp/'+fileName).iloc[:, 0]
    predicted_labels_new_model = np.array(predictions.split(',')[1:-1], dtype=str)
    # Calculate the model accuracy
    accuracy = (predicted_labels_new_model == target_labels).sum() / len(target_labels)
    print("accuracy: ", accuracy)

    # Update DynamoDB Table with accuracy value
    dynamo = boto3.resource('dynamodb')
    table = dynamo.Table(event['Input']['DynamoDBTable'])
    try:
      response = table.update_item(
        Key={
          'RunId': event['Input']['Model']
        },
        UpdateExpression="set Accuracy = :a, ecrImageTag = :e",
        ExpressionAttributeValues={
          ':a': (str(accuracy)),
          ':e': ecrTag
        },
        ReturnValues="UPDATED_NEW"
      )
      logger.debug(json.dumps(response))
    except:
      e = sys.exc_info()[0]
      f = sys.exc_info()[1]
      g = sys.exc_info()[2]
      logger.error("error (update error): "+str(e) + str(f) + str(g))