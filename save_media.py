import os,cv2

import multiprocessing
import time
from utils import save_file
from AGdb.database import database
from AGdb.create_tables import Stream_Details, Stream_Details_Raw


# global settings
static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/')
out_static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/')


# s3_save settings
no_of_processes = 1
DEFAULT_BUCKET = "kuvrr-analytics-test"
DEFAULT_S3_Folder = '/static'

# monitor settings
# set Stream = False for finite streaming. Setting STREAM = True will ignore TOTAL_ITERATIONS
# Total_ITERATIONS is the number of files that will be written to S3
TOTAL_ITERATIONS = 1100
STREAM = False


no_of_processes = 1
# put 2 to skip every other frame. 1 no skip
skip_frames = 20


def monitor(filename,manifest_name,segment_name,start_number):
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

    raw_file = static_dir + filename.format(start_number)
    while True and True if STREAM  == True  else ( start_number <= TOTAL_ITERATIONS):

        if os.path.isfile(raw_file) == True:
            if i == 0:
                # do this only once for the entire session!
                # This is to warm up ffmpeg with frame shape
                #raw_file = static_dir + filename + '_rawfile' + str(start_number) + '.mkv'
                raw_file = static_dir + filename.format(start_number)
                capture = cv2.VideoCapture(raw_file)
                ret, frame = capture.read()
                # the first mkv file might be a dud. In case all these steps will fail
                # until increment counter sets to next good file
                if ret:
                    h, w, c = frame.shape
                    ffmpegwriter = FFMPEG_VideoWriter(logfile, w, h, static_dir, manifest_name, segment_name, 30)
                    capture.release()
                    i = 1
                else:
                    print('-->dud fragment skipping')

            print('Processing', raw_file )
            capture = cv2.VideoCapture(raw_file)
            skip_counter = 0

            while (capture.isOpened()):
                try:
                    ret, frame = capture.read()
                    timer(capture)
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
                        # TODO uncomment the ffmpegwriter
                        ffmpegwriter.write_frame(frame)
                        #TODO needs to assign all .TS files created in this call to the TS associated with the rawfile
                        skip_counter = skip_counter + 1
                        # TODO save meta data info

                    else:
                        capture.release()
                        cv2.destroyAllWindows()
                        break
                    #TODO save meta data
                    #print('saving HLS file to S3')
                except:
                    print('-->dud fragment skipping')

            start_number = start_number + 1
            raw_file = static_dir + filename.format(start_number)

        else:
            if i == 0:
                print('-->Initial run. File not found. Waiting for 10 sec')
                time.sleep(10)
                print('Done Sleeping')
            else:
                print('-->Middle run. File not found. Waiting for 1 sec')
                time.sleep(.1)
                print('Done Sleeping')



    # need to close everything and save one last time
    capture.release()
    cv2.destroyAllWindows()
    ffmpegwriter.close()
    return

def timer(cap):
    time = cap.get(cv2.CAP_PROP_POS_MSEC)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    index = cap.get(cv2.CAP_PROP_POS_FRAMES)

    #print('time,',time, ',fps,',fps, ',tf,',total_frames,',index,',index)
    print('time in sec,', time/1000,  ',%,', index/total_frames)


def test():

    # Create a VideoCapture object and read from input file
    # If the input is the camera, pass 0 instead of the video file name
    cap = cv2.VideoCapture('C:/Users/Jaison/PycharmProjects/Agimage/static/best_2_1000.m3u8')

    # Check if camera opened successfully
    if (cap.isOpened() == False):
        print("Error opening video stream or file")

    # Read until video is completed
    while (cap.isOpened()):
        # Capture frame-by-frame
        ret, frame = cap.read()
        if ret == True:

            # Display the resulting frame
            #cv2.imshow('Frame', frame)
            timer(cap)
            # Press Q on keyboard to  exit
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break

        # Break the loop
        else:
            break

    # When everything done, release the video capture object
    cap.release()

    # Closes all the frames
    cv2.destroyAllWindows()

if __name__ == "__main__":
    print('Run save media first to warm up the GPUs and then only start stream and get_media')
    pool = multiprocessing.Pool(processes=no_of_processes)

    camera_id = '2'
    db = database(camera_id)

    filename = 'test_' + str(camera_id) + '_rawfile{:08d}.mkv'

    # get next value for manifest based on camera id which is instantiated above
    meta_data_instance = db.get_analytics_metaData_object('manifest_next_value')
    i = int(meta_data_instance.value)

    manifest_name = 'best_'+ str(camera_id) +'_' + str(i) + ''+ '.m3u8'
    # segment_name = 'best_200_{:06d}.ts'
    #segment_name = 'best_200_'
    segment_name = 'best_'+ str(camera_id) +'_' + str(i) + '_'
    start_number = int(db.get_analytics_metaData_object('raw_file_prev_value').value)

    # Test harness
    #monitor(filename,manifest_name,segment_name,start_number)
    test()