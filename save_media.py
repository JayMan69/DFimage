import os,cv2
from Image_Recognize import draw_bound_box
from ffmpeg_writer import FFMPEG_VideoWriter
import multiprocessing
import time
from utils import save_file


static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/kvs/')
filename = 'test.mkv'
start_number = 0
out_static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/kvs/')
manifest_name = 'best.m3u8'

# same as _200_%06d.ts
segment_name = 'best_200_{:06d}.ts'

DEFAULT_BUCKET = "kuvrr-analytics-test"
DEFAULT_S3_Folder = '/static'

# set Stream = False for finite streaming. Setting STREAM = True will ignore TOTAL_ITERATIONS
TOTAL_ITERATIONS = 10
STREAM = False

global p
global no_of_processes
no_of_processes = 1


def monitor(filename,manifest_name,segment_name,start_number):
    # program to monitor static folder for .mkv files as they are being written out
    # by get_media.py

    print('First file to start with',filename,start_number)

    raw_file = static_dir + filename + '_rawfile' + str(start_number) + '.mkv'
    logfile = open('logfile' + ".log", 'w+')
    i = 0
    h, w, c = 0
    start_number = 0
    # you need CTRL C to quit this program
    queue_value = multiprocessing.Queue()
    queue_value.put(('Start',out_static_dir+segment_name))
    run_parallel(True,queue_value)

    while True and True if STREAM  == True  else ( start_number <= TOTAL_ITERATIONS):
        try:
            if os.path.isfile(raw_file) == True:
                if i == 0:
                    # do this only once for the entire session!
                    # This is to warm up ffmpeg with frame shape
                    raw_file = static_dir + filename + '_rawfile' + str(start_number) + '.mkv'
                    capture = cv2.VideoCapture(raw_file)
                    ret, frame = capture.read()
                    h, w, c = frame.shape
                    ffmpegwriter = FFMPEG_VideoWriter(logfile, w, h, static_dir, filename, segment_name, 30)
                    capture.release()
                    i = 1

                raw_file = static_dir + filename + '_rawfile' + str(start_number) + '.mkv'
                start_number = start_number + 1
                capture = cv2.VideoCapture(raw_file)
                while (capture.isOpened()):
                    ret, frame = capture.read()
                    if ret:
                        frame = draw_bound_box(frame)
                        ffmpegwriter.write_frame(frame)
                        # TODO save meta data info

                    else:
                        capture.release()
                        cv2.destroyAllWindows()
                        break
                #TODO
                print('saving HLS file to S3')

        except KeyboardInterrupt:
            # need to close everything and save one last time
            capture.release()
            cv2.destroyAllWindows()
            ffmpegwriter.close()
            queue_value.put('Q')
            run_parallel(False, queue_value)
            exit()

    queue_value.put('Q')
    run_parallel(False,queue_value)

def save_to_S3(queue):
    # Look for files in the folder
    # As they appear push them to S3
    # If no more files, sleep and check for files again and if not found Also check queue to quit
    # TODO Need to store start in db to support more than one process concurrently

    quit = False
    try_counts = 0
    first = 0
    start =  start_number

    # Loops ends when quit == True and try_counts > 2
    while True and (False if (quit == True and try_counts > 2) else True):
        # First call gets the file format
        if first == 0:
            value1 = queue.get(block=False, timeout=.002)
            file = value1[1]
            value = value1
            pid = os.getpid()
            first = 1
        else:
            try:
                value = queue.get(block=False, timeout=.002)
            except:
                value = ''

        if value == 'Q' :
            # check for files for a certain number of time and then quit
            try_counts = try_counts + 1
            time.sleep(5)
            quit = True
            # set value so that it does not enter this loop again.
            # We will set Trycounts to higher number in the next statement that checks if any more files exist
            # print('Nothing more to process and received quit signal')
            #return

        file1 = file.format(start)
        if os.path.isfile(file1) == True:
            print('Saving file to S3', pid, file1, time.time())
            save_file(file1, DEFAULT_BUCKET, DEFAULT_S3_Folder)
            # save manifest
            save_file(value[1], DEFAULT_BUCKET, DEFAULT_S3_Folder)
            start = start + 1
        else:
            # did not find a file. Increase ty_counts
            if try_counts > 0: try_counts = try_counts + 1

    print('In queue finished processing ', pid, value, time.time())
    # process exits when done
    return

def run_parallel(initial_setup, queue_value):

    no_of_processes = 1
    global p

    if initial_setup == True:

        p = multiprocessing.Pool(no_of_processes, save_to_S3, (queue_value,))

    if initial_setup == False:
        for i in range(0, no_of_processes):
            queue_value.put('Q')
        queue_value.close()
        p.close()
        # This will block until all sub processes are done
        p.join()



if __name__ == "__main__":
    print('Main does nothing')


# Test harness
monitor(filename,manifest_name,segment_name,start_number)