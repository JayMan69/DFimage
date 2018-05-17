import boto3
import json

DEFAULT_BUCKET = "kuvrr-analytics-test"

#arn:aws:kinesisvideo:[a-z0-9-]+:[0-9]+:[a-z]+/[a-zA-Z0-9_.-]+/[0-9]+
DEFAULT_ARN = ''
session = boto3.Session(profile_name='agimage')

def get_kvs_stream(selType = 'EARLIEST', arn = DEFAULT_ARN):
    kinesis_client = session.client('kinesisvideo')

    response = kinesis_client.get_data_endpoint(
        StreamARN = arn,
        APIName = 'GET_MEDIA'
    )

    video_client = session.client('kinesis-video-media',
                                endpoint_url=response['DataEndpoint']
    )

    # 'StartSelectorType': 'FRAGMENT_NUMBER'|'SERVER_TIMESTAMP'|'PRODUCER_TIMESTAMP'|'NOW'|'EARLIEST'|'CONTINUATION_TOKEN',
    stream = video_client.get_media(
        StreamARN=DEFAULT_ARN,
        StartSelector={'StartSelectorType': selType}
    )

    # use 'Body' if Payload does not work
    # stream['Body'].read()
    datafeedstreamBody = stream['Payload'].read()
    #stream['Body'].read()
    # returns boto3.streamingBody or big blob. See below to return in chunks

    # x=stream['Body']
    # y = x.read(amt=500)

    return datafeedstreamBody


def get_s3_file(key, bucket=DEFAULT_BUCKET):
    #client = boto3.client('s3')
    client = session.client('s3')

    try:
        response = client.get_object(
            Bucket = bucket,
            Key = key
        )

        print (response)
        return response

    except:
        print("File not found on S3 for key: " + key)
        return None


def save_data(key, body, content_type, bucket=DEFAULT_BUCKET):

    print('Saving data to: ' + key + ' bucket: ' + bucket)

    #client = boto3.client('s3')
    client = session.client('s3')


    try:
        response = client.put_object(
            Bucket = bucket,
            Key = key,
            Body = body,
            ContentType = content_type
        )

    except Exception as e:
        print("Error saving file to S3: " + str(e))


# Test harnesses
#get_s3_file('test-images/Birds.jpg')
#body = {
#'name':'jaison',
#'game': 'badi'
#}

#save_data('test.json',json.dumps(body),'application/json')