from camera import Video


def gen(camera):
    while True:
        #frame = camera.get_frame()
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')




@app.route('/image_feed')
def image_feed():
    print('in image_feed')
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
