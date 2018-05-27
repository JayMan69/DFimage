import boto3
import json
import sys,os
import time
from datetime import datetime

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

#oregon / us-west-2
DEFAULT_ARN = 'arn:aws:kinesisvideo:us-west-2:519480889604:stream/analytics-test-1/1526562027624'
# kvs is written to us-west-2
session = boto3.Session(profile_name='agimage1')


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


    # TODO need to read continuation_token from DB
    continuation_token = '91343852333181486911561392739977168453738419308'

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

    static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/kvs/')
    filename = 'test.mkv'



    w = 320
    h = 240
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
        index = 0
        datafeedstreamBody = stream['Payload'].read(amt=read_amt)
        ldf = len(datafeedstreamBody)
        # last position processed
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
                    #print('Last token found', last_c_token)
                    raw_file = open(static_dir + filename + '_rawfile' +str(i) +'.mkv', 'wb')
                    i = i + 1
                    write_buffer = write_buffer + datafeedstreamBody[last_pos:c_t_e_pos]
                    last_pos = c_t_e_pos
                    index = last_pos
                    raw_file.write(write_buffer)
                    raw_file.close()
                    write_buffer = b''



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
            raw_file = open(static_dir + filename + '_rawfile' + str(i) + ' .mkv', 'wb')
            raw_file.write(write_buffer)
            raw_file.close()
            break

    print('success and done!')


import multiprocessing
import time

data = (
    ['a', '2'], ['b', '4'], ['c', '6'], ['d', '8'],
    ['e', '1'], ['f', '3'], ['g', '5'], ['h', '7']
)

def mp_worker(inputs, the_time):
    print (" Processs %s\tWaiting %s seconds" % (inputs, the_time))
    time.sleep(int(the_time))
    print (" Process %s\tDONE" % inputs)

def mp_handler():
    p = multiprocessing.Pool(2)
    p.map(mp_worker, data)

if __name__ == '__main__':
    mp_handler()

# Test harness 1
#date = datetime.strptime('2018-05-23 6:4:27', '%d/%m/%y %H:%M:%S')
#get_kvs_stream('PRODUCER_TIMESTAMP',DEFAULT_ARN,date)

# Test harness 2
#get_kvs_stream('EARLIEST',DEFAULT_ARN,'')

# Test harness 3 use continuation token from db
get_kvs_stream('',DEFAULT_ARN,'')
