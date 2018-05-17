from time import time
from time import sleep
import cv2


class Camera(object):
    def __init__(self):
        self.frames = [open('./images/'+f + '.jpg', 'rb').read() for f in ['1', '2', '3']]
        print('opened frames',len(self.frames),type(self.frames))

    def get_frame(self):
        # note this shows the same image because we are in the same second for approx 13 - 30 times
        v = int(time()) % 3
        print ('returning image frame' , v)

        sleep(1/30)
        return self.frames[v]

class Video(object):
    def __init__(self):
        self.video = cv2.VideoCapture('./video/unify1.mp4')
        total_frames = self.video.get(cv2.CAP_PROP_FRAME_COUNT)
        print('opened video with frame count ', total_frames)

    def __del__(self):
        self.video.release()

    def get_v_frame(self):
        success, image = self.video.read()
        if not success: print('Failing')
        print ('returning video frame')
        return cv2.imencode('.jpg', image)[1].tobytes()


#new = Camera()
#test = new.frames()
#print ('done')

