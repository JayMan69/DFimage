import cv2
from darkflow.net.build import TFNet
import matplotlib.pyplot as plt
import numpy as np
import time
import sys
import utils
import json
import time
import datetime
from ffmpeg_writer import FFMPEG_VideoWriter
import os

#%config InlineBackend.figure_format = 'svg'
if sys.platform == 'win32':
    print ('Setting windows options')
    options = {
        'model': 'cfg/yolo.cfg',
        'load': 'bin/yolov2.weights',
        'threshold': 0.3
    }
else:
    print('Setting unix options')
    options = {
        'model': 'cfg/yolo.cfg',
        'load': 'bin/yolov2.weights',
        'threshold': 0.3,
        'gpu' : 1
    }

labels = ['person','knife']
#labels = ['knife','refrigerator']
colors = {'person':(0,0,0),'knife':(0,0,255)}
#colors = {'knife':(0,0,255),'refrigerator':(0,0,255)}

tfnet = TFNet(options)

def picture_process_label(resource,start_time):

    tfnet = TFNet(options)
    elapsed_time = time.time() - start_time
    print('Time to load model',elapsed_time)
    # read the color image and covert to RGB
    img = cv2.imread(resource, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


    # use YOLO to predict the image
    a = datetime.datetime.now()
    result = tfnet.return_predict(img)
    b = datetime.datetime.now()
    delta = b - a
    print('Time to predict in milliseconds', int(delta.total_seconds() * 1000))

    for x in range (0,len(result)) :
        print (result[x])



def picture_process_display(resource,start_time):

    tfnet = TFNet(options)
    elapsed_time = time.time() - start_time
    print('Time to load model',elapsed_time)
    # read the color image and covert to RGB
    img = cv2.imread(resource, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # save original picture to show
    img1 = cv2.imread(resource, cv2.IMREAD_COLOR)
    img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)

    # use YOLO to predict the image
    a = datetime.datetime.now()
    result = tfnet.return_predict(img)
    b = datetime.datetime.now()
    delta = b - a
    print('Time to predict in milliseconds', int(delta.total_seconds() * 1000))

    for x in range (0,len(result)) :
        print (result[x])
        tl = (result[x]['topleft']['x'], result[x]['topleft']['y'])
        # adjust lettering to be below top of screen
        if result[x]['topleft']['y'] == 0 :
            tl1 = (result[x]['topleft']['x'], 10)
        else:
            tl1 = (result[x]['topleft']['x'], result[x]['topleft']['y'])
        br = (result[x]['bottomright']['x'], result[x]['bottomright']['y'])
        label = result[x]['label']

        # add the box and label and display it
        img = cv2.rectangle(img, tl, br, (0, 255, 0), 17)
        img = cv2.putText(img, label, tl1, cv2.FONT_HERSHEY_DUPLEX, .5, (0, 0, 0), 1)
    #plt.plot(img)
    #plt.show()
    #plt.imshow([img, img1])
    plt.subplot(1,2,1);
    plt.imshow(img)
    plt.subplot(1,2,2);
    plt.imshow(img1)
    plt.show()



def video_process(resource):
    # TODO move to initialization function when moving to a lambda
    tfnet = TFNet(options)

    capture = cv2.VideoCapture(resource)
    total_frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)

    print ('Total frames ', total_frames )
    # frame number starts from 0 to total_frames - 1
    i = 0
    results = []
    counter = 0
    start_time = time.time()
    x = 1  # displays the frame rate every 1 second
    while (capture.isOpened()):

        ret, frame = capture.read()
        counter += 1
        if (time.time() - start_time) > x:
            print("FPS: ", counter / (time.time() - start_time))
            counter = 0
            start_time = time.time()



        if ret:
            result = tfnet.return_predict(frame)
            results.append((i,result))
            #print ("Processed frame %s of %s" %(i ,total_frames))
            i = i + 1
        else:
            capture.release()
            save_meta_data('','','application/json',resource+'.json',results)
            break

def dumper(obj):
    try:
        return obj.toJSON()
    except:
        if str(type(obj)) == "<class 'numpy.float32'>":
            return obj.item()
        else:
            return obj.__dict__

def save_meta_data(client,id,type,resource,results):
    print ('Saving JSON to S3')
    #result = json.dumps(results)
    # fix to convert numpy float to float
    result = json.dumps(results, default=dumper)
    # get filename from the path + filename
    utils.save_data(os.path.basename(resource),result,type)


def video_bound_box(resource,filename,segment_name ):
    # process to create bounded video and save
    # TODO pass a parameter to show video too
    # TODO need to move tfnet out of each
    logfile = open('logfile' + ".log", 'w+')
    static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/')
    capture = cv2.VideoCapture(resource)
    i = 0
    counter = 0
    start_time = time.time()
    start_time1 = time.time()
    x = 1

    while (capture.isOpened()):
        ret, frame = capture.read()
        if i == 0:
            # open ffmpeg writer once
            # need to put this in the loop to read shape
            h, w, c = frame.shape
            # TODO need to pass the -r parameter from stream meta data
            ffmpegwriter = FFMPEG_VideoWriter(logfile,w,h,static_dir,filename,segment_name,30)
        if ret:
            frame = draw_bound_box(frame)
            ffmpegwriter.write_frame(frame)
            i = i + 1
        else:
            print('Completed processing. Closing everything')
            print("Processing time: ", (time.time() - start_time1))
            capture.release()
            cv2.destroyAllWindows()
            ffmpegwriter.close()
            break

        counter += 1
        if (time.time() - start_time) > x:
            print(" FPS: ", counter / (time.time() - start_time), end="", flush=True)
            counter = 0
            start_time = time.time()

    logfile.close()

def draw_bound_box(frame,last_frame_results,reprint):
    #colors = [tuple(255 * np.random.rand(3)) for i in range(5)]
    if reprint == False:
        results = tfnet.return_predict(frame)
    else:
        results = last_frame_results

    for result in  results:
        tl = (result['topleft']['x'], result['topleft']['y'])
        br = (result['bottomright']['x'], result['bottomright']['y'])
        label = result['label']
        if label in labels :
            # only certain labels put bound boxes
            frame = cv2.rectangle(frame, tl, br, colors[label], 2)
            frame = cv2.putText(frame, label, tl, cv2.FONT_HERSHEY_COMPLEX, .3, (0, 0, 0), 2)

    if reprint == False:
        return frame, results
    else:
        # redraw old results on new frame
        return frame, ''



def main():
    #TODO need to clean up main function
    if len(sys.argv) == 1:
        print('Default')
    else:
        if len(sys.argv) == 2:
            variable = sys.argv[1].split('=')
            if variable[0] == '--resource':
                resource = variable[1]
                print('resource =', resource)

            if variable[0] == '--type':
                type = variable[1]
                print('type =', type)


        else:
            if len(sys.argv) == 3:
                print('2 input variables')
                print (sys.argv)

            variable = sys.argv[1].split('=')
            #print(variable)
            if variable[0] == '--resource':
                #print('in resource')
                resource = variable[1]
                print('resource =', resource)

                variable2 = sys.argv[2].split('=')
                type = variable2[1]
                print('type =', type)

            else:
                if variable[0] == '--type':
                    #print('in type')
                    type = variable[1]
                    print('type =', type)
                    variable2 = sys.argv[2].split('=')
                    resource = variable2[1]
                    print('resource =', resource)
        #exit()
        if type == 'video':
            video_process(resource)
        else:
            print ('process picture ', resource)
            #exit()
            picture_process_display(resource)


#main()

# Test harnesses
start_time = time.time()
# your code

#picture_process_display('./images/Bird.jpg',start_time)
#picture_process_label('./images/Bird.jpg',start_time)
#print('Completed time',time.time() - start_time)
#video_process('./video/unify1.mp4')

#video_bound_box('./video/b2b.mp4','seg.m3u8','seg')

#video_bound_box('./static/kvs/test.mkv_rawfile40.mkv','seg.m3u8','seg')