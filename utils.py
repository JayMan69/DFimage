import boto3
import json

DEFAULT_BUCKET = "kuvrr-analytics-test"


#virginia / us-east-1
#DEFAULT_ARN ='arn:aws:kms:us-east-1:519480889604:key/6882aa49-a7b0-48b3-a9c0-a28b0482f662'
DEFAULT_ARN ='arn:aws:kinesisvideo:us-east-1:519480889604:stream/analytics-test-1/1526308999982'
session = boto3.Session(profile_name='agimage')

#oregon / us-west-2
#DEFAULT_ARN = 'arn:aws:kms:us-west-2:519480889604:key/dee07eca-6793-4b7e-baf1-af91ce4bc10e'
# kvs is written to us-west-2
#session = boto3.Session(profile_name='agimage1')



def get_kvs_stream(selType = 'EARLIEST', arn = DEFAULT_ARN):
    kinesis_client = session.client('kinesisvideo')

    response = kinesis_client.list_streams()
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
    datafeedstreamBody = stream['Payload'].read(amt=500)
    print('success')
    
    # stream into stdin of ffmpeg
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

    print ('Success')

# Test harnesses
#get_s3_file('test-images/Birds.jpg')
body = {
'name':'jaison',
'game': 'badi'
}

#save_data('test.json',json.dumps(body),'application/json')

get_kvs_stream()