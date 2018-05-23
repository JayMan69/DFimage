import boto3
import json
import sys,os
from ffmpeg_writer import FFMPEG_VideoWriter1

DEFAULT_BUCKET = "kuvrr-analytics-test"


#virginia / us-east-1
#DEFAULT_ARN ='arn:aws:kinesisvideo:us-east-1:519480889604:stream/analytics-test-1/1526308999982'
#session = boto3.Session(profile_name='agimage')

#oregon / us-west-2
DEFAULT_ARN = 'arn:aws:kinesisvideo:us-west-2:519480889604:stream/analytics-test-1/1526562027624'
# kvs is written to us-west-2
session = boto3.Session(profile_name='agimage1')



def get_kvs_stream(selType = 'EARLIEST', arn = DEFAULT_ARN):
    kinesis_client = session.client('kinesisvideo')
    # use response to find the correct end point
    #response = kinesis_client.list_streams()

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
    i = 0
    logfile = open('logfile1' + ".log", 'w+')
    static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/kvs/')
    filename = 'test.m3u8'
    segment_name = 'test'

    ffwrite = FFMPEG_VideoWriter1(logfile,static_dir,filename,segment_name)
    read_amt = 640*480*3*30*1 #(h*w*no. of pixels*fps*60 seconds worth)
    while True:
        datafeedstreamBody = stream['Payload'].read(amt=read_amt)
        ffwrite.write_frame(datafeedstreamBody)
        print(sys.getsizeof(datafeedstreamBody),i)
        i = i +1
        if sys.getsizeof(datafeedstreamBody) < read_amt:
            print('exiting with total bytes pulled =' , read_amt*i)
            break

    print('success')

    # stream into stdin of ffmpeg
    #return datafeedstreamBody


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