import boto3
import json
import sys,os
import time
from datetime import datetime
import subprocess
import multiprocessing,random
from AGdb.database import database
from AGdb.create_tables import Stream_Details, Stream_Details_Raw

f_n = b'AWS_KINESISVIDEO_FRAGMENT_NUMBERD'
f_n_s =b'\x87\x10\x00\x00/'
f_n_e =b'\xc8'

# end of fragment. New fragment is starting
c_t = b'AWS_KINESISVIDEO_CONTINUATION_TOKEND'
c_t_s = b'\x87\x10\x00\x00/'
c_t_s_len1 = len(c_t + c_t_s)
c_t_e = b'\x1aE'

no_of_processes = 1
s_t = b'AWS_KINESISVIDEO_SERVER_TIMESTAMPD'
s_t_s = b'\x87\x10\x00\x00\x0e'
s_t_e = b'g'
s_t_e_len = len(s_t) + len(s_t_s)


#virginia / us-east-1
#DEFAULT_ARN ='arn:aws:kinesisvideo:us-east-1:519480889604:stream/analytics-test-1/1526308999982'
#session = boto3.Session(profile_name='agimage')
#w = 640
#h = 480


#oregon / us-west-2
DEFAULT_ARN = 'arn:aws:kinesisvideo:us-west-2:519480889604:stream/analytics-test-1/1527325436792'
#DEFAULT_ARN = 'arn:aws:kinesisvideo:us-west-2:519480889604:stream/demo-stream/1526732311448'
# kvs is written to us-west-2
session = boto3.Session(profile_name='agimage1')
w = 1280
h = 720
camera_id = '2'
# TODO need to read continuation_token from DB
continuation_token = '91343852333181486911561392739977168453738419308'

static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/')
filename = 'test_rawfile{:08d}.mkv'

def get_kvs_stream(pool,selType , arn = DEFAULT_ARN, date='' ):
    # get camera id given arn name
    db = database(camera_id)
    stream_instance = db.get_stream_object('arn',arn)

    kinesis_client = session.client('kinesisvideo')
    #use response object below to find the correct end point
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
    else:
        # old stream. Check if stream details record exists or not
        p_object = Stream_Details
        p_object.stream_id = stream_instance.id
        p_object.start_time = datetime.strptime('2018-06-1 9:02:02', '%Y-%m-%d %H:%M:%S')
        instance = db.get_stream_details_object('start_time', p_object)

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
        write_buffer,last_c_token,i = process_stream(datafeedstreamBody, static_dir, filename,i, write_buffer,db,instance,pool)

        #print(sys.getsizeof(datafeedstreamBody),j)
        #j = j +1
        counter += 1
        if (time.time() - start_time) > onesecond:
            #print('Last token found', last_c_token)
            #print("Bytes processed per second: ", read_amt / (counter / (time.time() - start_time)), end="", flush=True)
            print("MB processed per second: ", (read_amt/1024/1024) / (counter / (time.time() - start_time)))
            counter = 0
            start_time = time.time()

        if sys.getsizeof(datafeedstreamBody) < read_amt:
            print('Exiting with total bytes pulled =' , read_amt*i)
            #TODO need to sleep here if streaming - because program might be pulling faster than ingest
            break

    print('Streaming done!')


class Object(object):
    pass

def process_stream(datafeedstreamBody,static_dir,filename,i,write_buffer,db,instance,pool):
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
                    r_file = filename.format(i)
                    i = i + 1
                    write_buffer = write_buffer + datafeedstreamBody[last_pos:c_t_e_pos]
                    last_pos = c_t_e_pos
                    index = last_pos
                    raw_file.write(write_buffer)
                    raw_file.close()
                    p_object = Object()
                    p_object.datastream = write_buffer
                    p_object.rawfile = r_file
                    p_object.instance = instance
                    # make the p_object iterable by adding a comma
                    pool.map(save_raw, (p_object,))
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
                r_file = filename.format(i)
                i = i + 1
                write_buffer = write_buffer + datafeedstreamBody[last_pos:c_t_e_pos]
                last_pos = c_t_e_pos
                index = last_pos
                raw_file.write(write_buffer)
                raw_file.close()
                p_object = Object()
                p_object.datastream = write_buffer
                p_object.rawfile = r_file
                p_object.instance = instance
                # make the p_object iterable by adding a comma
                pool.map(save_raw, (p_object,))
                write_buffer = b''

    return write_buffer, last_c_token,i


def save_raw(p_object):
    #http://chriskiehl.com/article/parallelism-in-one-line/
    #https://stackoverflow.com/questions/22411424/python-multiprocessing-pool-map-typeerror-string-indices-must-be-integers-n


    if hasattr(p_object, 'datastream'):

        db = database(camera_id)
        datastream = p_object.datastream
        stream_details_instance = p_object.instance
        rawfile = p_object.rawfile

        st_start_index = datastream.find(s_t)
        st_end_index = datastream.find(s_t_e, st_start_index)
        start_time = datastream[st_start_index+s_t_e_len:st_end_index]
        start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(float(start_time))))
        #2018-06-01 09:02:02
        p1_object = Stream_Details_Raw
        p1_object.stream_details_id = stream_details_instance.id
        p1_object.rawfilename = rawfile
        p1_object.server_time = start_time
        db.put_stream_details_raw(p1_object)
        print('finished save_raw', start_time, rawfile)


if __name__ == "__main__":
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!Remember to put the correct H W or program will crash!!!!!')
    print('!!!!Running with ',h,w)
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    pool = multiprocessing.Pool(processes=no_of_processes)
    #pool = []


    # Test harness 1
    date = datetime.strptime('2018-06-1 9:02:02', '%Y-%m-%d %H:%M:%S')
    get_kvs_stream(pool,'PRODUCER_TIMESTAMP',DEFAULT_ARN,date)

    # Test harness 2
    #get_kvs_stream(pool,'EARLIEST',DEFAULT_ARN,'')

    # Test harness 3 use continuation token from db
    #get_kvs_stream(pool,'',DEFAULT_ARN,'')

    # Test live stream
    #get_kvs_stream(pool,'NOW',DEFAULT_ARN,'')

    # os.system('ffplay -i test_rawfile00000150.mkv -vf "cropdetect=24:160:0"')
    # output is
    #AWS_KINESISVIDEO_SERVER_TIMESTAMP: 1528483898.375
    #AWS_KINESISVIDEO_PRODUCER_TIMESTAMP: 1528483898.329
    # will have to break into the smallest rawfiles based on a singular server_timestamp
    # how to assign that to the correct TLS???