import os
import cv2
import numpy as np
import argparse
from multiprocessing.connection import Listener
from multiprocessing.connection import Client
address = ('localhost', 6000)


def open_video_send_frames(videoName):
    # run receive_messages first
    # Open video and send each frame details and data via a socket
    # TODO need to check if client is on before sending. Currently send frames will just hang
    try:
        conn = Client(address)
    except:
        print("open a listener first")
        exit()

    cap = cv2.VideoCapture(videoName)
    # set this to 0 if you want to send everything
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_send_frame_count = 100
    send_frame_count = 0


    while (cap.isOpened()):
        ret, frame_rgb = cap.read()
        h, w, d = frame_rgb.shape
        #frame_gbr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        message = {
            'type' : 'data',
            'h': h,
            'w': w,
            'd': d,
            'bytes': frame_rgb
        }

        #TODO Test code. Remove
        #cv2.imshow('original frame', frame_rgb)
        #cv2.waitKey(1) & 0xFF
        #f = get_frame(h,w,d,bytes)
        #show_frame(f)

        conn.send(message)
        if total_send_frame_count > 0:
            send_frame_count = send_frame_count + 1
            if send_frame_count == total_send_frame_count :
                break

    # all frames done. Time to send EOF
    message = {
        'type' : 'eof',
        'h': 0,
        'w': 0,
        'd': 0,
        'bytes': 0
    }

    conn.send(message)
    # can also send arbitrary objects:
    # conn.send(['a', 2.5, None, int, sum])
    conn.close()

    cap.release()
    cv2.destroyAllWindows()

def receive_messages():
    # Open socket and receive each frame details and data via a socket
    # close socket if 'close' message is received
    listener = Listener(address)
    conn = listener.accept()
    print  ('connection accepted from', listener.last_accepted)
    while True:
        msg = conn.recv()
        # do something with msg
        if msg['type'] == 'eof':
            conn.close()
            break
        else:
            # got a frame and do something with it
            h = msg['h']
            w = msg['w']
            d= msg['d']
            b = msg['bytes']
            frame = get_frame (h,w,d,b)
            show_frame(frame)
    listener.close()
    cv2.destroyAllWindows()

def get_frame(height,width,depth,bytes):
    h = height
    w = width
    d = depth
    imageString = bytes

    # convert array string into numpy array
    array = np.fromstring(imageString, dtype=np.uint8)
    # reshape numpy array into the required dimensions
    frame = array.reshape((h, w, d))

    #nparr = np.fromstring(imageString, np.uint8)
    #img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)  # cv2.IMREAD_COLOR in OpenCV 3.1
    #img_np = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)

    # test the images and remove these lines
    return frame

def show_frame(frame):
    cv2.imshow('frame', frame)
    cv2.waitKey(33)


def main():
    FUNCTION_MAP = {'o': open_video_send_frames,
                    'r': receive_messages,
                    }
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=FUNCTION_MAP.keys())
    args = parser.parse_args()
    func = FUNCTION_MAP[args.command]
    print (func.__name__)
    if func.__name__ == 'open_video_send_frames':
        print ('running open_video_send_frames')
        open_video_send_frames('./video/unify1.mp4')
    else:
        print('running receive_messages')
        receive_messages()

if __name__ == '__main__':
    # Note this script is always run with command line option o
    main()