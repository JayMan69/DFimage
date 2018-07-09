import boto3
import json
import sys,os
import time
from datetime import datetime
import multiprocessing,random
from AGdb.database import database
from AGdb.create_tables import Stream_Details, Stream_Details_Raw
from copy import deepcopy

f_n = b'AWS_KINESISVIDEO_FRAGMENT_NUMBERD'
f_n_s =b'\x87\x10\x00\x00/'
f_n_e =b'\xc8'

# end of fragment. New fragment is starting
c_t = b'AWS_KINESISVIDEO_CONTINUATION_TOKEND'
c_t_s = b'\x87\x10\x00\x00/'
c_t_s_len1 = len(c_t + c_t_s)
c_t_e = b'\x1aE'
continuation_token = '91343852333181486911561392739977168453738419308'
c_t_full_len = len(c_t) + len(c_t_s) + len(continuation_token)


no_of_processes = 2
s_t = b'AWS_KINESISVIDEO_SERVER_TIMESTAMPD'
s_t_s = b'\x87\x10\x00\x00\x0e'
s_t_e = b'g'
s_t_e_len = len(s_t) + len(s_t_s)

p_t = b'AWS_KINESISVIDEO_PRODUCER_TIMESTAMPD'
p_t_s = b'\x87\x10\x00\x00\x0e'
p_t_e = b'\x1fC'
p_t_e_len = len(p_t) + len(p_t_s)


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

def get_kvs_stream(pool,selType , arn = DEFAULT_ARN, date='' ):
    # get camera id given arn name
    filename = 'test_' +str(camera_id)+ '_rawfile{:08d}.mkv'

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
        stream_details_instance = Object()
        stream_details_instance.stream_id = stream_instance.id
        stream_details_instance.live = True
        stream_details_instance.resolution = str(w) + 'x' + str(h) + 'x3'
    else:
        # old stream. Check if stream details record exists or not
        p_object = Object()
        p_object.id = stream_instance.id
        p_object.start_time = date
        stream_details_instance = db.get_stream_details_object('start_time', p_object)
        if stream_details_instance is None:
            # new stream details instance
            stream_details_instance = Stream_Details()
            stream_details_instance.stream_id = stream_instance.id
            stream_details_instance.live = 'Process'
            stream_details_instance.resolution = str(w) + 'x' + str(h) + 'x3'
            stream_details_instance = db.put_stream_details(stream_details_instance)
        else:
            print('Session details exist with same timestamp!!!! Exiting!')
            exit()
        # Note this amount might not be exactly correct because the data is already compressed
    read_amt = h*w*3*1*1 #(h*w*no. of pixels*fps*1 seconds worth)

    #TODO need i to be in db otherwise will continue to overwrite files
    meta_data_instance = db.get_analytics_metaData_object('raw_file_next_value')
    i = int(meta_data_instance.value)
    start_i = deepcopy(i)
    # get some time variables
    onesecond = 1
    counter = 1
    start_time = time.time()
    excess_buffer = b''
    # end of timing variables
    first_time = True
    p_temp_object = Object()
    p_temp_object.id = stream_details_instance.id
    db.session.close()
    results = {}
    final_results = {}
    while True:

        datafeedstreamBody = stream['Payload'].read(amt=read_amt)
        fullstream = excess_buffer + datafeedstreamBody
        index = 0
        p_objects =[]
        while True:
            start_pos = fullstream.find(c_t,index)
            # see if you have a continuation token in the stream
            if start_pos > -1:
                fragment = fullstream[index:start_pos + c_t_full_len]
                excess_buffer = fullstream[start_pos + c_t_full_len:]
                p_object = Object()
                p_object.static_dir = static_dir
                p_object.filename = filename
                p_object.datafeedstreamBody = fragment
                p_object.i = deepcopy(i)
                p_object.instance = {'id':p_temp_object.id}
                p_objects.append(p_object)
                index = start_pos + c_t_full_len
                i = i + 1

            else:

                #process_stream_efficiently(p_object)
                results = pool.map(process_stream_efficiently, (p_objects))
                if first_time == True:
                    # get the timestamp of the first file for saving later on
                    for a in results:
                        for key in a :
                            k1 = key
                            v1 = a[key]
                            final_results.update({k1:v1})


                break

        if first_time == True:
            # print('first time is still on')
            # TODO find if the first rawfile table has been inserted. If its inserted take that TS and update
            if start_i in  final_results:
                stream_details_instance = db.session.query(Stream_Details).get(p_temp_object.id)
                stream_details_instance.start_time = final_results[start_i][1]
                db.session.commit()
                first_time = False
            db.session.close()
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
            #TODO write excess out
            break

    print('Streaming done!')
    pool.close()
    pool.join()
    # Note we are using max statement here because its a one time only
    db = database(camera_id)
    et = db.get_stream_details_raw('max_time', p_temp_object.id)[0]
    if et != None:
        stream_details_instance = db.session.query(Stream_Details).get(p_temp_object.id)
        stream_details_instance.end_time = et
        stream_details_instance.live = 'False'
        db.session.commit()
        instance = db.get_analytics_metaData_object('raw_file_next_value')
        instance.value = str(i)
        db.session.commit()


class Object(object):
    pass

def process_stream_efficiently(p_object):
    # This process expects exactly one Fragment and writes out only one file
    if hasattr(p_object, 'datafeedstreamBody'):
        datafeedstreamBody = p_object.datafeedstreamBody
        static_dir = p_object.static_dir
        filename = p_object.filename
        i = p_object.i
        instance = p_object.instance

        raw_file = open(static_dir + filename.format(i), 'wb')
        r_file = filename.format(i)
        write_buffer = datafeedstreamBody
        raw_file.write(write_buffer)
        raw_file.close()
        start_time,id = prep_data_raw(write_buffer, r_file, instance)
    return {i: (id,start_time)}


def prep_data_raw(write_buffer,r_file,instance):
    # get server time
    st_start_index = write_buffer.find(s_t)
    st_end_index = write_buffer.find(s_t_e, st_start_index)
    start_time = write_buffer[st_start_index + s_t_e_len:st_end_index]
    start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(float(start_time))))

    # get producer time
    pt_start_index = write_buffer.find(p_t)
    pt_end_index = write_buffer.find(p_t_e, pt_start_index)
    pstart_time = write_buffer[pt_start_index + p_t_e_len:pt_end_index]
    pstart_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(float(pstart_time))))


    p_object = Object()
    p_object.start_time = start_time
    p_object.producer_time = pstart_time
    p_object.rawfile = r_file
    p_object.instance = instance
    p_object.type = 'Stream_Details_Raw'
    # make the p_object iterable by adding a comma
    #pool.map(save_raw, (p_object,))
    id = save_raw(p_object)
    return start_time,id

def save_raw(p_object):
    #http://chriskiehl.com/article/parallelism-in-one-line/
    #https://stackoverflow.com/questions/22411424/python-multiprocessing-pool-map-typeerror-string-indices-must-be-integers-n

    if p_object.type == 'Stream_Details_Raw':
        db = database(camera_id)
        id = p_object.instance['id']
        rawfile = p_object.rawfile
        start_time  = p_object.start_time
        pstart_time = p_object.producer_time

        p1_object = Stream_Details_Raw
        p1_object.stream_details_id = id
        p1_object.rawfilename = rawfile
        p1_object.server_time = start_time
        p1_object.producer_time = pstart_time
        row = db.put_stream_details_raw(p1_object)
        retval = row.id
        db.session.close()
        return retval
        #print('finished Stream_Details_Raw', os.getpid(), start_time, rawfile)

    elif p_object.type == 'Stream_Details':
        #db = database(camera_id)
        if p_object.operation == 'Update':
            print ('update')
        else:
            print('insert')

        print('finished Stream_Details', os.getpid())

    elif p_object.type == 'Analytics_MetaData':
        print('update')

        print('finished updating Analytics_MetaData', os.getpid())

if __name__ == "__main__":
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!Remember to put the correct H W or program will crash!!!!!')
    print('!!!!Running with ',w,h)
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    pool = multiprocessing.Pool(processes=no_of_processes)

    ## Test harness 1
    ## Time shown on KVS is UTC - 5
    ## Time sent to KVS is UTC!
    ## Time is not sensitive of upto 20s so if video ends at 49 you can get the video with a call of 55
    date = datetime.strptime('2018-06-1 14:14:35', '%Y-%m-%d %H:%M:%S')
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