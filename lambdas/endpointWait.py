import json, boto3, logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(json.dumps(event))

    endpoint=event['Input']['Endpoint']

    client = boto3.client('sagemaker')
    response = client.describe_endpoint(
        EndpointName=endpoint
    )
    logger.info(response['EndpointStatus'])

    if (response['EndpointStatus'] == 'InService'):
        statusCode = 200
        return {
            'ErrorCode': statusCode,
            'body': json.dumps('Amazon SageMaker endpoint is InService!')
        }
    else:
        raise NotInService('Amazon SageMaker endpoint not InService')
class NotInService(Exception): pass