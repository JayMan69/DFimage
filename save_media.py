import os,cv2
from Image_Recognize import draw_bound_box
from ffmpeg_writer import FFMPEG_VideoWriter
import multiprocessing
import time
from utils import save_file

# global settings
static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/')
out_static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/')


# s3_save settings
manifest_name = 'best.m3u8'
#segment_name = 'best_200_{:06d}.ts'
segment_name = 'best_200_'
start_number = 0
no_of_processes = 1
DEFAULT_BUCKET = "kuvrr-analytics-test"
DEFAULT_S3_Folder = '/static'

# monitor settings
# set Stream = False for finite streaming. Setting STREAM = True will ignore TOTAL_ITERATIONS
# Total_ITERATIONS is the number of files that will be written to S3
TOTAL_ITERATIONS = 10
STREAM = False
#filename = 'test.mkv'
filename = 'test_rawfile{:08d}.mkv'
no_of_processes = 1
# put 2 to skip every other frame. 1 no skip
skip_frames = 1


def monitor(filename,manifest_name,segment_name,start_number):
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
    # run_parallel(True,queue_value)
    counter = 0
    start_time = time.time()
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
                    counter += 1
                    if (time.time() - start_time) > x:
                        print("FPS: ", counter / (time.time() - start_time))
                        counter = 0
                        start_time = time.time()
                    if ret:
                        skip_counter = skip_counter  + 1
                        if skip_counter % skip_frames == 0:
                            frame = draw_bound_box(frame)
                        ffmpegwriter.write_frame(frame)
                        # TODO save meta data info
                        #  TODO use boundbox from previous frame
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
            print('-->file not found. Waiting for 10 sec')
            time.sleep(10)
            print('Done Sleeping')




    # need to close everything and save one last time
    capture.release()
    cv2.destroyAllWindows()
    ffmpegwriter.close()
    # queue_value.put('Q')
    # run_parallel(False, queue_value)
    return

    # queue_value.put('Q')
    # run_parallel(False,queue_value)

def save_to_S3(queue):
    # Look for files in the folder
    # As they appear push them to S3
    # If no more files, sleep and check for files again and if not found Also check queue to quit
    # TODO Need to store start in db to support more than one process concurrently
    #

    quit = False
    try_counts = 0
    first = 0
    # global setting
    start =  start_number

    while True and (False if (quit == True and try_counts > 2) else True):
        #logfile.write('In while loop, quit, try_counts'+str(quit)+str(try_counts))
        #print('In while loop, quit, try_counts',quit,try_counts)
        # First call gets the file format
        if first == 0:
            value1 = queue.get(block=False, timeout=.002)
            manifest = value1[0]
            file = value1[1]
            print('--->>> Start signal with file', file)
            value = value1
            pid = os.getpid()
            first = 1

        else:
            # second call can be a None or Q
            try:
                value = queue.get(block=False, timeout=.02)
            except:
                value = ''

        if value == 'Q' :
            # check for files for a certain number of time and then quit
            time.sleep(1)
            quit = True
            #logfile.write('--->>> Quit is true')
            print('--->>> Quit signal')
            try_counts = try_counts + 1
            # print('Nothing more to process and received quit signal')
            #return


        file1 = file.format(start)
        if os.path.isfile(file1) == True:
            print('Saving file to S3', pid, file1, time.time())
            save_file(file, DEFAULT_BUCKET, DEFAULT_S3_Folder)

            # save manifest
            save_file(manifest, DEFAULT_BUCKET, DEFAULT_S3_Folder)
            start = start + 1
        else:
            # did not find a file. Increase try_counts
            if try_counts > 0: try_counts = try_counts + 1


    print('In queue finished processing ', pid, value, time.time())
    return

class run_parallel():
    def __init__(self, initial_setup, queue_value):
        print('-->In init with', initial_setup)
        self.p = multiprocessing.Pool(no_of_processes, save_to_S3, (queue_value,))
        self.initial_setup = initial_setup

    def run(self,initial_setup, queue_value):
        print('-->In run with',initial_setup)
        if initial_setup == 'Q':
            for i in range(0, no_of_processes):
                print('--->putting new values', i)
                queue_value.put('Q')
                #print('queue put',queue.get())
            queue_value.close()
            print('closing p')
            self.p.close()
            # This will block until all sub processes are done
            print('at p.join')
            self.p.join()


if __name__ == "__main__":
    print('Run save media first to warm up the GPUs and then only start stream and get_media')


# Test harness
monitor(filename,manifest_name,segment_name,start_number)