from multiprocessing import Process, Lock, Value, Array
from threading import Thread
import sys
import ctypes
import numpy as np
import cv2
from flask import Flask, render_template, Response, request
#from flask_socketio import SocketIO, send, emit

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

frame = np.ctypeslib.as_array(Array(ctypes.c_uint8, SCREEN_HEIGHT * SCREEN_WIDTH * 3).get_obj()).reshape(SCREEN_HEIGHT, SCREEN_WIDTH, 3)
stopped = Value(ctypes.c_bool, False)

def get_from_stream():
    stream = cv2.VideoCapture(0)
    stream.set(cv2.CAP_PROP_FPS, 30)

    while True:
        if stopped.value:
            stream.release()
            return

        _, frame_raw = stream.read()
        frame[:] = frame_raw

Process(target=get_from_stream).start()

# web server
app = Flask(__name__)


def gen():
    while True:
        yield (b'--frame\r\n'
               # b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')
               b'Content-Type: image/jpeg\r\n\r\n' + cv2.imencode('.jpg', frame_marked)[1].tobytes() + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


thread_flask = Thread(target=app.run, kwargs=dict(debug=False, threaded=True))  # threaded Werkzeug server
thread_flask.daemon = True
thread_flask.start()

while True:
    if stopped.value:
        sys.exit(0)
    frame_bytes = cv2.imencode('.jpg', frame)[1].tobytes()
    frame_marked = frame