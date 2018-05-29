import os,cv2
from Image_Recognize import draw_bound_box
from ffmpeg_writer import FFMPEG_VideoWriter

def monitor(filename,manifest_name,segment_name,start_number):
    # program to monitor static folder for .mkv files as they are being written out
    # by get_media.py
    static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/kvs/')
    print('First file to start with',filename,start_number)

    raw_file = static_dir + filename + '_rawfile' + str(start_number) + '.mkv'
    logfile = open('logfile' + ".log", 'w+')
    i = 0
    h = 0
    w = 0
    c = 0
    # you need CTRL C to quit this program
    while True:
        try:
            if os.path.isfile(raw_file) == True:
                if i == 0:
                    # do this only once for the entire session!
                    ret, frame = capture.read()
                    h, w, c = frame.shape
                    ffmpegwriter = FFMPEG_VideoWriter(logfile, w, h, static_dir, filename, segment_name, 30)
                    capture.release()
                    i = 1

                raw_file = static_dir + filename + '_rawfile' + str(start_number) + '.mkv'
                start_number += 1
                capture = cv2.VideoCapture(raw_file)
                while (capture.isOpened()):
                    ret, frame = capture.read()
                    if ret:
                        frame = draw_bound_box(frame)
                        ffmpegwriter.write_frame(frame)
                    else:
                        capture.release()
                        cv2.destroyAllWindows()
                        break

        except KeyboardInterrupt:
            # need to close everything and save one last time
            capture.release()
            cv2.destroyAllWindows()
            ffmpegwriter.close()

# Test harness
filename = 'test.mkv'
start_number = 0
manifest_name = 'seg.m3u8'
segment_name = 'seg'
monitor(filename,manifest_name,segment_name,start_number)