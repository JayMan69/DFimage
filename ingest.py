import boto3
import cv2
from utils import get_kvs_stream
import numpy as np
import subprocess as sp
import os , tempfile

# 'StartSelectorType': 'FRAGMENT_NUMBER'|'SERVER_TIMESTAMP'|'PRODUCER_TIMESTAMP'|'NOW'|'EARLIEST'|'CONTINUATION_TOKEN',
def readstream_does_not_work ():
        FFMPEG_BIN = "ffmpeg"  # on Linux ans Mac OS
        FFMPEG_BIN = "ffmpeg.exe"  # on Windows

        datafeed = get_kvs_stream()

        # Method 1
        # Need to get a frame not fragments as below
        data = np.fromstring(datafeed, dtype=np.uint8)
        imagedisp = cv2.imdecode(data, 1)

        # Method 2
        command = [ FFMPEG_BIN,
                '-y', # (optional) overwrite output file if it exists
                '-f', 'rawvideo',
                '-vcodec','rawvideo',
                '-pix_fmt', 'rgb24',
                '-i', '-', # The imput comes from a pipe
                '-an', # Tells FFMPEG not to expect any audio
                '-vcodec', 'mpeg', # mpeg is the output format
                'my_output_videofile.mp4' ]

        pipe = sp.Popen( command, stdin=sp.PIPE, stderr=sp.PIPE)
        pipe.proc.stdin.write(datafeed.tostring())
        pipe.stdin.close()
        pipe.wait()


def readpipe(rf,l):
        fifo = rf.read(l)
        #path = "/tmp/my_program.fifo"
        #fifo = open(path, "r")
        cap = cv2.VideoCapture(fifo)
        try:
                while True:
                    # Capture frame-by-frame
                    ret, frame = cap.read()
                    if ret:
                        average_color_per_row = np.average(frame, axis=0)
                        average_color = np.average(average_color_per_row, axis=0)
                        print(average_color)
        finally:
                # When everything done, release the capture
                cap.release()


def create_pipe(path):
# works only in unix
        datafeed = get_kvs_stream()


        tmpdir = tempfile.mkdtemp()
        filename = os.path.join(tmpdir, 'myfifo')
        print (filename)
        try:
            os.mkfifo(filename)
        except OSError as e:
            print ("Failed to create FIFO: %s" % e)
        else:
            fifo = open(filename, 'w')
            # write stuff to fifo
            fifo.write(datafeed)
            readpipe()
            fifo.close()
            os.remove(filename)
            os.rmdir(tmpdir)

def create_pipe2():
        r, w = os.pipe()
        rf, wf = os.fdopen(r, 'rb', 0), os.fdopen(w, 'wb', 0)
        datafeed = get_kvs_stream()
        l = wf.write(datafeed)
        # need to read same number of bytes as write to not hang


def get_chunks_of_S3_data():
        # S3 reads returns StreamingBody object with of type generator. Following code reads and returns a chunk
        s3_response = s3_client.get_object(Bucket=BUCKET, Key=FILENAME)

        def generate(result):
                for chunk in iter(lambda: result['Body'].read(self.CHUNK_SIZE), b''):
                        yield chunk

        def another_way():
                get_file = s3_response._raw_stream

        def another_way1():
                body = s3_response.get()["Body"]
                import io
                buff_reader = io.BufferedReader(body._raw_stream)
                import pickle
                data_dict = pickle.load(buff_reader)

        def another_way2():
                import boto3
                import json

                client = boto3.client('iot-data', region_name='us-east-1')
                response = client.get_thing_shadow(thingName='pump1')

                streamingBody = response["payload"]
                jsonState = json.loads(streamingBody.read())

                print (jsonState)

                print (jsonState["state"]["reported"]["pump_mode"])