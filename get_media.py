import boto3
import json
import sys,os
import time
from datetime import datetime
import subprocess
import multiprocessing,random

f_n = b'AWS_KINESISVIDEO_FRAGMENT_NUMBERD'
f_n_s =b'\x87\x10\x00\x00/'
f_n_e =b'\xc8'

# end of fragment. New fragment is starting
c_t = b'AWS_KINESISVIDEO_CONTINUATION_TOKEND'
c_t_s = b'\x87\x10\x00\x00/'
c_t_s_len1 = len(c_t + c_t_s)
c_t_e = b'\x1aE'

#virginia / us-east-1
#DEFAULT_ARN ='arn:aws:kinesisvideo:us-east-1:519480889604:stream/analytics-test-1/1526308999982'
#session = boto3.Session(profile_name='agimage')
#w = 640
#h = 480


#oregon / us-west-2
#DEFAULT_ARN = 'arn:aws:kinesisvideo:us-west-2:519480889604:stream/analytics-test-1/1527325436792'
DEFAULT_ARN = 'arn:aws:kinesisvideo:us-west-2:519480889604:stream/demo-stream/1526732311448'
# kvs is written to us-west-2
session = boto3.Session(profile_name='agimage1')
w = 640
h = 480
# TODO need to read continuation_token from DB
continuation_token = '91343852333181486911561392739977168453738419308'

static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/')
filename = 'test_rawfile{:08d}.mkv'

def get_kvs_stream(selType , arn = DEFAULT_ARN, date='' ):
    kinesis_client = session.client('kinesisvideo')

    #use response object below to find the correct end point
    # TODO will need to find stream name given client and camera id
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



    if selType == '':
        # get stream from last continuation token
        stream = video_client.get_media(
            StreamARN=DEFAULT_ARN,
            StartSelector={'StartSelectorType': 'CONTINUATION_TOKEN','ContinuationToken': continuation_token}
        )

    if selType == 'EARLIEST':
        # get stream from last continuation token
        stream = video_client.get_media(
            StreamARN=DEFAULT_ARN,
            StartSelector={'StartSelectorType': 'EARLIEST'}
        )

    if selType == 'PRODUCER_TIMESTAMP':
        # get stream from last time
        stream = video_client.get_media(
            StreamARN=DEFAULT_ARN,
            StartSelector={'StartSelectorType': 'SERVER_TIMESTAMP','StartTimestamp': date}
        )

    if selType == 'NOW':
        stream = video_client.get_media(
            StreamARN=DEFAULT_ARN,
            StartSelector={'StartSelectorType': 'NOW'}
        )




    # Note this amount might not be exactly correct because the data is already compressed
    read_amt = h*w*3*1*1 #(h*w*no. of pixels*fps*1 seconds worth)

    #TODO need i to be in db otherwise will continue to overwrite files
    i = 0
    #j = 0
    write_buffer = b''
    # get some time variables
    onesecond = 1
    counter = 1
    start_time = time.time()
    # end of timing variables

    while True:

        datafeedstreamBody = stream['Payload'].read(amt=read_amt)
        # make call to run_parallel here including using i as start
        write_buffer,last_c_token,i = process_stream(datafeedstreamBody, static_dir, filename,i, write_buffer)

        #print(sys.getsizeof(datafeedstreamBody),j)
        #j = j +1
        counter += 1
        if (time.time() - start_time) > onesecond:
            print('Last token found', last_c_token)
            #print("Bytes processed per second: ", read_amt / (counter / (time.time() - start_time)), end="", flush=True)
            print("Bytes processed per second: ", read_amt / (counter / (time.time() - start_time)))
            counter = 0
            start_time = time.time()

        if sys.getsizeof(datafeedstreamBody) < read_amt:
            print('Exiting with total bytes pulled =' , read_amt*i)
            #TODO need to sleep here if streaming - because program might be pulling faster than ingest
            break

    print('Streaming done!')

def process_stream(datafeedstreamBody,static_dir,filename,i,write_buffer):
    # writes out begining of valid video (\x1aE\) until AWS_KINESISVIDEO_CONTINUATION_TOKEND end
    index = 0
    ldf = len(datafeedstreamBody)
    # last position processed
    last_pos = 0
    while index < ldf:
        index = datafeedstreamBody.find(c_t, index)
        if index == -1:
            if last_pos == 0:
                write_buffer = write_buffer + datafeedstreamBody
            else:
                # flush write_buffer and get ready to add from next read stream
                write_buffer = datafeedstreamBody[last_pos:]
            break
        else:
            # print('continuation token found')
            c_t_e_pos = datafeedstreamBody.find(c_t_e, index + c_t_s_len1)
            if c_t_e_pos == -1:
                # Check if we can get the same token length as last time
                # if so its end of file
                # write
                new_last_c_token = datafeedstreamBody[(index + c_t_s_len1):]
                if len(new_last_c_token) == len(last_c_token):
                    last_c_token = new_last_c_token
                    raw_file = open(static_dir + filename.format(i) , 'wb')
                    i = i + 1
                    write_buffer = write_buffer + datafeedstreamBody[last_pos:c_t_e_pos]
                    last_pos = c_t_e_pos
                    index = last_pos
                    raw_file.write(write_buffer)
                    raw_file.close()
                    write_buffer = b''
                    break
                else:
                    # TODO fix this error condition. Remaining in next stream call
                    print('Need to fix this')

            else:
                last_c_token = datafeedstreamBody[(index + c_t_s_len1):c_t_e_pos]
                # print('Last token found', last_c_token)
                #raw_file = open(static_dir + filename + '_rawfile' + str(i) + '.mkv', 'wb')
                raw_file = open(static_dir + filename.format(i), 'wb')
                i = i + 1
                write_buffer = write_buffer + datafeedstreamBody[last_pos:c_t_e_pos]
                last_pos = c_t_e_pos
                index = last_pos
                raw_file.write(write_buffer)
                raw_file.close()
                write_buffer = b''

    return write_buffer, last_c_token,i

def run_ffmpeg(queue):
    while True:
        value = queue.get()
        pid = os.getpid()

        if value == 'Q':
            print('Nothing more to process', value)
            return
        else:
            # call to ffmpeg here
            cmd = 'ffmpeg -i ' + value[0] +  '-r 25 ' + value[1]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            #return (out, err)
            print('In queue finished processing ' , pid,value, time.time())


def run_parallel(initial_setup,queue_value):

    no_of_processes = 1

    if initial_setup == True:
        queue = multiprocessing.Queue()
        p = multiprocessing.Pool(no_of_processes,run_ffmpeg,(queue,))

    if queue_value == 'Q':
        for i in range(0, no_of_processes - 1):
            queue.put('Q')
        queue.close()
        p.close()
        # This will block until all sub processes are done
        p.join()

    else:
        queue.put(queue_value)

if __name__ == "__main__":
    print('Remember to put the correct H W or program will crash')



# Test harness 1
#date = datetime.strptime('2018-06-1 9:02:02', '%Y-%m-%d %H:%M:%S')
#get_kvs_stream('PRODUCER_TIMESTAMP',DEFAULT_ARN,date)

# Test harness 2
#get_kvs_stream('EARLIEST',DEFAULT_ARN,'')

# Test harness 3 use continuation token from db
#get_kvs_stream('',DEFAULT_ARN,'')

# Test live stream
get_kvs_stream('NOW',DEFAULT_ARN,'')
