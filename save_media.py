import os,cv2
from datetime import timedelta
import multiprocessing
import time
from AGdb.database import database
from AGdb.create_tables import Stream_Details
from copy import deepcopy

# global settings
static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/static/')
out_static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/static/')
camera_id = '2'
no_of_processes = 1
# put 2 to skip every other frame. 1 no skip
skip_frames = 20
# check to save every 5 frames
save_frames = 5

# monitor settings
# set Stream = False for finite streaming. Setting STREAM = True will ignore TOTAL_ITERATIONS
# Total_ITERATIONS is the number of files that will be written to S3
TOTAL_ITERATIONS = 2100
STREAM = False

# s3_save settings
DEFAULT_BUCKET = "kuvrr-analytics-test"
DEFAULT_S3_Folder = '/static'


def monitor(filename,manifest_name,segment_name,start_number,FPS,pool):
    from Image_Recognize import draw_bound_box
    from ffmpeg_writer import FFMPEG_VideoWriter
    # program to monitor static folder for .mkv files as they are being written out
    # by get_media.py

    print('First file to start with',filename.format(start_number),start_number)

    #raw_file = static_dir + filename + '_rawfile' + str(start_number) + '.mkv'
    logfile = open(static_dir + 'logfile' + ".log", 'w+')
    i = 0
    h = 0
    w = 0
    c = 0
    # you need CTRL C to quit this program
    # queue_value = multiprocessing.Queue()
    # queue_value.put(('Start',out_static_dir+segment_name))

    counter = 0
    start_time = time.time()
    last_video_time = 0
    x = 1  # displays the frame rate every 1 second
    total_frame_counter = 0
    group_id = 0
    previous_frame_results =''
    raw_file = static_dir + filename.format(start_number)
    while True and True if STREAM  == True  else ( start_number <= TOTAL_ITERATIONS):

        if os.path.isfile(raw_file) == True:
            if i == 0:
                # do this only once for the entire session!
                # This is to warm up ffmpeg with frame shape
                raw_file = static_dir + filename.format(start_number)
                capture = cv2.VideoCapture(raw_file)
                ret, frame = capture.read()
                # the first mkv file might be a dud. In case all these steps will fail
                # until increment counter sets to next good file
                if ret:
                    h, w, c = frame.shape
                    ffmpegwriter = FFMPEG_VideoWriter(logfile, w, h, static_dir, manifest_name, segment_name, FPS)
                    capture.release()
                    i = 1
                    db = database(camera_id)
                    instance = db.get_stream_details_raw('rawfilename',filename.format(start_number))
                    stream_details_raw_start_time = instance[0]
                    stream_details_id = instance[1]
                    stream_details_instance = db.session.query(Stream_Details).get(stream_details_id)
                    stream_details_instance.manifest_file_name = manifest_name
                    db.session.commit()
                    db.session.close()
                    Mypreprocobj = preprocessor_object(stream_details_raw_start_time,stream_details_id,FPS)
                else:
                    print('-->dud fragment skipping')

            print('Processing', raw_file )
            capture = cv2.VideoCapture(raw_file)
            skip_counter = 0

            while (capture.isOpened()):
                try:
                    ret, frame = capture.read()
                    counter += 1
                    if (time.time() - start_time) > x:
                        print("FPS: ", counter / (time.time() - start_time))
                        counter = 0
                        start_time = time.time()
                    if ret:

                        if skip_counter % skip_frames == 0 or skip_counter == 0:
                            # reprint = False
                            frame,last_frame_results = draw_bound_box(frame,'',False)
                        else:
                            # reprint = True
                            frame, last_frame_results  = draw_bound_box(frame, last_frame_results, True)

                        ffmpegwriter.write_frame(frame)
                        skip_counter = skip_counter + 1
                        if total_frame_counter % save_frames == 0:

                            if last_frame_results != None and last_frame_results !='':
                                # write to metadata table only if there are results
                                if compare_labels(previous_frame_results,last_frame_results) == False:
                                    group_id = group_id + 1

                                pobj = Object()
                                pobj.total_frame_counter = deepcopy(total_frame_counter)
                                pobj.last_frame_results = deepcopy(last_frame_results)
                                pobj.group_id = deepcopy(group_id)
                                pobj.Mypreprocobj = Mypreprocobj
                                #save_meta_data(pobj)
                                pool.map(save_meta_data, (pobj,))
                            else:
                                if previous_frame_results != None and previous_frame_results != '':
                                    group_id = group_id + 1

                            previous_frame_results = last_frame_results
                        total_frame_counter = total_frame_counter + 1
                    else:
                        capture.release()
                        cv2.destroyAllWindows()
                        break

                except Exception as e:
                    print(e)
                    #print('-->dud fragment skipping')

            start_number = start_number + 1
            raw_file = static_dir + filename.format(start_number)

        else:
            if i == 0:
                print('-->Initial run. File not found. Waiting for 10 sec')
                time.sleep(10)
                print('Done Sleeping')
            else:
                print('-->Middle run. File not found. Waiting for .1 sec')
                time.sleep(.1)
                print('Done Sleeping')
                if check_done_live(stream_details_id,filename.format(start_number-1)) == True:
                    #break out of the while loop
                    break


    # need to close everything and save one last time

    pool.close()
    pool.join()

    if i == 0:
        print('Need to increase TOTAL_ITERATIONS value!!')
    else:

        capture.release()
        cv2.destroyAllWindows()
        ffmpegwriter.close()

        db = database(camera_id)
        instance = db.get_analytics_metaData_object('manifest_next_value')
        instance.value = str(int(instance.value)+1)
        db.session.commit()
        instance = db.get_analytics_metaData_object('raw_file_prev_value')
        instance.value = start_number
        db.session.commit()
        print('Saving done!')
    return

def timer(cap):
    time = cap.get(cv2.CAP_PROP_POS_MSEC)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    index = cap.get(cv2.CAP_PROP_POS_FRAMES)

    #print('time,',time, ',fps,',fps, ',tf,',total_frames,',index,',index)
    print('time in sec,', time/1000,  ',%,', index/total_frames)

def check_done_live(stream_details_id,last_file_name_processed):
    db = database(camera_id)
    stream_details_instance = db.session.query(Stream_Details).get(stream_details_id)
    if stream_details_instance.live == False or stream_details_instance.live == 'False':
        # If False then done. Otherwise can be True or Process
        rawf = db.get_stream_details_raw('max_rawfilename',stream_details_id)
        if rawf[0] == last_file_name_processed:
            print('End of feed')
            db.session.close()
            return True
        else:
            db.session.close()
            return False
    else:
        # process still running
        db.session.close()
        return False

class Object(object):
    pass


class preprocessor_object():
    def __init__(self,time,stream_details_id,FPS):
        # self.group_id = 1
        # self.last_sec = 0
        # self.last_sec_labels = ''
        self.start_time = time
        self.stream_details_id = stream_details_id
        self.FPS = FPS



def save_meta_data(pobj):
    db = database(camera_id)
    p_object = Object()
    p_object.stream_details_id = pobj.Mypreprocobj.stream_details_id
    p_object.frame_number = pobj.total_frame_counter
    p_object.timestamp = pobj.Mypreprocobj.start_time + timedelta(seconds=pobj.total_frame_counter/pobj.Mypreprocobj.FPS)
    p_object.seconds = pobj.total_frame_counter/pobj.Mypreprocobj.FPS
    for row in pobj.last_frame_results:
        p_object.label = row['label']
        p_object.confidence = row['confidence']
        p_object.position = {'topleft' : row['topleft'], 'bottomright' : row['bottomright']}
        p_object.group_id = pobj.group_id
        db.put_stream_metadata(p_object)
    print('saved ', p_object.timestamp, ' by ', os.getpid())
    db.session.close()
    return

def compare_labels(last_labels,current_labels):
    # Note these two will not match!!!
    #labels1 = ['clock', 'person']
    #labels2 = ['clock', 'person', 'clock']
    last_label_list = []
    current_label_list = []
    for rows in last_labels:
        last_label_list.append(rows['label'])
    for rows in current_labels:
        current_label_list.append(rows['label'])

    if last_label_list == current_label_list:
        return True
    else:
        return False


if __name__ == "__main__":
    print('Run save media first to warm up the GPUs and then only start stream and get_media')
    pool = multiprocessing.Pool(processes=no_of_processes)


    db = database(camera_id)

    filename = 'test_' + str(camera_id) + '_rawfile{:08d}.mkv'

    # get next value for manifest based on camera id which is instantiated above
    meta_data_instance = db.get_analytics_metaData_object('manifest_next_value')
    i = int(meta_data_instance.value)

    manifest_name = 'best_'+ str(camera_id) +'_' + str(i) + ''+ '.m3u8'
    segment_name = 'best_'+ str(camera_id) +'_' + str(i) + '_'
    start_number = int(db.get_analytics_metaData_object('raw_file_prev_value').value)
    FPS = 30
    # Test harness
    monitor(filename,manifest_name,segment_name,start_number,FPS,pool)
