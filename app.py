#!/usr/bin/env python
from flask import Flask, render_template, Response
from camera import Camera
from camera import Video

app = Flask(__name__,static_url_path='/static')



@app.route('/')
def index():
    #return render_template('index.html')
    #return 'http://localhost:5000/video_feed'
    return render_template('video.html')

@app.route('/video_feed')
def video_feed():
    def gen(video):
        while True:
            frame = video.get_v_frame()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    print('in video_feed')
    return Response(gen(Video()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')




#TODO need to replace with gevent or like server
# e.g.
#uwsgi --http :8080 -w app
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
    #app.run(host='0.0.0.0', server='gevent')