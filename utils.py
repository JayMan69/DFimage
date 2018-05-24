import boto3
import json
import sys,os
from ffmpeg_writer import FFMPEG_VideoWriter1

DEFAULT_BUCKET = "kuvrr-analytics-test"

f_n = b'AWS_KINESISVIDEO_FRAGMENT_NUMBERD'
f_n_s =b'\x87\x10\x00\x00/'
f_n_e =b'\xc8'

# end of fragment. New fragment is starting
c_t = b'AWS_KINESISVIDEO_CONTINUATION_TOKEND'
c_t_s = b'\x87\x10\x00\x00/'
c_t_s_len1 = len(c_t + c_t_s)
c_t_e = b'\x1aE'
# everything except for the c_t_e is the token number. c_t_e should be part of the new file

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
    # stream = video_client.get_media(
    #     StreamARN=DEFAULT_ARN,
    #     StartSelector={'StartSelectorType': selType}
    # )

    from datetime import datetime
    date = datetime.strptime('2017-05-04', "%Y-%m-%d")
    date = date.replace(minute=4, hour=6, second=27, year=2018, month=5, day=23)

    continuation_token = '91343852333181486911561392739977168453738419308'

    if continuation_token == None:
        # get stream from last time
        stream = video_client.get_media(
            StreamARN=DEFAULT_ARN,
            StartSelector={'StartSelectorType': 'SERVER_TIMESTAMP','StartTimestamp': date}
        )
    else:
        # get stream from last continuation token
        stream = video_client.get_media(
            StreamARN=DEFAULT_ARN,
            StartSelector={'StartSelectorType': 'CONTINUATION_TOKEN','ContinuationToken': continuation_token}
        )



    # use 'Body' if Payload does not work
    # stream['Body'].read()
    i = 0
    logfile = open('logfile1' + ".log", 'w+')
    static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/kvs/')
    filename = 'test.mkv'
    segment_name = 'test'


    w = 320
    h = 240
    #ffwrite = FFMPEG_VideoWriter1(logfile,static_dir,filename,segment_name,h,w)
    read_amt = h*w*3*1*1 #(h*w*no. of pixels*fps*1 seconds worth)
    #TODO need i to be in db otherwise will continue to overwrite files
    i = 0
    j = 0
    write_buffer = b''
    while True:
        index = 0
        datafeedstreamBody = stream['Payload'].read(amt=read_amt)
        ldf = len(datafeedstreamBody)
        last_pos = 0
        while index < ldf:
            index = datafeedstreamBody.find(c_t, index)
            if index == -1 :
                if last_pos == 0:
                    write_buffer = write_buffer + datafeedstreamBody
                else:
                    # flush write_buffer and get ready to add from next read stream
                    write_buffer = datafeedstreamBody[last_pos:]
                break
            else:
                #print('continuation token found')
                c_t_e_pos = datafeedstreamBody.find(c_t_e, index + c_t_s_len1)
                if c_t_e_pos == -1 :
                    # TODO fix this error condition. Remaining in next stream call
                    print('Need to fix this')
                else:
                    last_c_token = datafeedstreamBody[(index + c_t_s_len1):c_t_e_pos]
                    print('writing output for last token', last_c_token)
                    raw_file = open(static_dir + 'rawfile' +str(i) +'.mkv', 'wb')
                    i = i +1
                    write_buffer = write_buffer + datafeedstreamBody[last_pos:c_t_e_pos]
                    last_pos = c_t_e_pos
                    index = last_pos
                    raw_file.write(write_buffer)
                    raw_file.close()
                    write_buffer = b''



        print(sys.getsizeof(datafeedstreamBody),j)
        j = j +1
        if sys.getsizeof(datafeedstreamBody) < read_amt:
            print('Exiting with total bytes pulled =' , read_amt*i)
            raw_file = open(static_dir + 'rawfile' + str(i) + ' .mkv', 'wb')
            raw_file.write(write_buffer)
            raw_file.close()
            break

    print('success and done!')



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