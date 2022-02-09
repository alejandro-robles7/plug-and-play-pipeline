import json, boto3, uuid, logging, sys, os
from datetime import datetime, timezone

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(json.dumps(event))
    
    # Trigger from S3 bucket postfix: train/iris.csv (so we only get one run)
    dataBucket = event['Records'][0]['s3']['bucket']['name']

    # Trigger verifies that train/iris.csv exists, next verify that validation/iris.csv exists
    # logger.info(event['Records'][0]['s3']['object']['key'])
    trainKey = event['Records'][0]['s3']['object']['key']
    # split the key and find the 'folder' that all the objects were loaded into
    keyPrefix = trainKey.split("/")[0]
    # logger.info(keyPrefix)
    validationFilePrefix = '/validation/iris.csv'
    #Not running the trigger task for v1.0 of the training data.
    if keyPrefix == 'v1.0':
        logger.info("Not initiating the training job for v1.0")
        pass
    else:
        # Make sure the object exists
        s3 = boto3.resource('s3')
        try:
            object = s3.Object(dataBucket,keyPrefix+validationFilePrefix).load()
        except:
            e = sys.exc_info()[0]
            f = sys.exc_info()[1]
            g = sys.exc_info()[2]
            logger.error("error (head error 404): "+str(e) + str(f) + str(g))
            raise

        # Second find latest ECR image
        repositoryName = os.environ['ecrModelRepo']

        ecr = boto3.client('ecr')
        response = ecr.describe_images(
            repositoryName=repositoryName
        )

        # Number of ECR images:
        # logger.info(len(response['imageDetails']))
        
        try:
            len(response['imageDetails'][0])
        except:
            e = sys.exc_info()[0]
            f = sys.exc_info()[1]
            g = sys.exc_info()[2]
            logger.error("error (No ECR images found): "+str(e) + str(f) + str(g))
            raise

        images = {}
        pubTime = 0
        for image in response['imageDetails']:
            # logger.info(image['imagePushedAt'])
            # logger.info(image['imageTags'][0])
            # Converting the datetime object to unixtime stamp because its way easier to math.
            if datetime.timestamp(image['imagePushedAt']) > pubTime:
                imageTag = image['imageTags'][0]
                pubTime = image['imagePushedAt'].timestamp()
            images[image['imageDigest']] = {'pushTime': image['imagePushedAt'], 'tag': image['imageTags'][0]} 
            # print("======")

        # logger.info(imageTag)

        accountId = context.invoked_function_arn.split(":")[4]
        region = os.environ['AWS_REGION']
        ecrArn = accountId+'.dkr.ecr.'+region+'.amazonaws.com/'+repositoryName+':'+imageTag

        # Third trigger the Step Function
        stateMachineArn = os.environ['trainingStateMachine']
        buildId = str(uuid.uuid4()) # If event is empty, then create this using uuid
        functionInput = {
            'BuildId': buildId, 
            'Job': 'Job-'+buildId, 
            'Model': 'Model-'+buildId, 
            'Endpoint': 'Endpoint-'+buildId, 
            'ecrArn': ecrArn,
            'dataBucketPath': 's3://'+dataBucket+'/'+keyPrefix+'/train', 
            'triggerSource': 'S3 data upload',
            'DynamoDBTable': os.environ['DynamoDBTable'],
            'commitId': 'NA',
            'authorDate': str(datetime.now()) }

        sf = boto3.client('stepfunctions')
        response = sf.start_execution(
            stateMachineArn=stateMachineArn,
            name=buildId,
            input=json.dumps(functionInput)
        )

        return {
            'statusCode': 200,
            'body': json.dumps('Training Job Started')
        }