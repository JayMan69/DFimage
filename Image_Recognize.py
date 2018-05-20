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


def video_bound_box(resource):
    # process to create bounded video and save
    # TODO pass a parameter to show video too
    # TODO need to move tfnet out of each
    logfile = open('logfile' + ".log", 'w+')

    tfnet = TFNet(options)
    capture = cv2.VideoCapture(resource)
    colors = [tuple(255 * np.random.rand(3)) for i in range(5)]
    total_frames = capture.get(7)
    print ('Total frames ', total_frames )
    i = 0
    counter = 0
    start_time = time.time()
    x = 1  # displays the frame rate every 1 second
    while (capture.isOpened()):
        ret, frame = capture.read()
        if i == 0:
            # open ffmpeg writer once
            h, w, c = frame.shape
            ffmpegwriter = FFMPEG_VideoWriter(logfile,w,h)
        counter += 1
        if (time.time() - start_time) > x:
            print("FPS: ", counter / (time.time() - start_time))
            counter = 0
            start_time = time.time()

        if ret:
            results = tfnet.return_predict(frame)
            for color, result in zip(colors, results):
                tl = (result['topleft']['x'], result['topleft']['y'])
                br = (result['bottomright']['x'], result['bottomright']['y'])
                label = result['label']
                # TODO move label to config
                if label == 'person' or label =='tvmonitor':
                    frame = cv2.rectangle(frame, tl, br, color, 7)
                    frame = cv2.putText(frame, label, tl, cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 0), 2)
            ffmpegwriter.write_frame(frame)
            i = i + 1
            print('Current frame ', i )
            #cv2.imshow('frame', frame)
            #if cv2.waitKey(1) & 0xFF == ord('q'):
                #break
        else:
            capture.release()
            cv2.destroyAllWindows()
            logfile.close()
            ffmpegwriter.close()
            break

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

video_bound_box('./video/unify1.h264')