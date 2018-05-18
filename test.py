import os

r, w = os.pipe()
rf, wf = os.fdopen(r, 'rb', 0), os.fdopen(w, 'wb', 0)

l = wf.write(b'hello')

# need to read same number of bytes as write to not hang
rf.read(l)

#1
command = ["ffmpeg",
        '-y', # (optional) overwrite output file if it exists
        '-f', 'rawvideo',
        '-vcodec','rawvideo',
        '-pix_fmt', 'rgb24',
        '-i', '-', # The imput comes from a pipe
        '-an', # Tells FFMPEG not to expect any audio
        '-vcodec', 'mpeg',
        'my_output_videofile.mp4' ]
from subprocess import Popen, PIPE
proc = sp.Popen(command, stdin=sp.PIPE)
proc.stdin.write(x)
#self.proc.stdin.write(img_array.tobytes())
proc.stdin.close()
proc.wait()
# need to output to null  output, use subprocess.DEVNULL


#2 standard in write
command = ["ffmpeg",
           '-f', 'hls',
           '-c', 'copy',
           '-hls_time', '10',
           '-hls_flags', 'delete_segments',
           '-i', '-', # The imput comes from a pipe
           'index.m3u8' ]

# need to see what standard error here is
# pipped input is not going in
proc = sp.Popen(command, stdin=sp.PIPE)

proc.stdin.write(x.tostring())


proc.stdin.close()
proc.wait()

#3 standard out read
from subprocess import Popen, PIPE

with open("test.avi", "rb") as infile:
    p=Popen(["ffmpeg", "-i", "-", "-f", "matroska", "-vcodec", "mpeg4",
        "-acodec", "aac", "-strict", "experimental", "-"],
           stdin=infile, stdout=PIPE)
    while True:
        data = p.stdout.read(1024)
        if len(data) == 0:
            break
        # do something with data...
        print(data)
    print p.wait() # should have finisted anyway





#4 named pipes
import cv2
import numpy


def extract(path):
 cap = cv2.VideoCapture(path)
 fnum = 0
 while True:
  ret, frame = cap.read()
  if ret:
   average_color_per_row = numpy.average(frame, axis=0)
   average_color = numpy.average(average_color_per_row, axis=0)
   print(average_color)
  else:
   break
   print(average_color)
 cap.release()
 print ("done")

 FIFO = '/tmp/FIFO'

 #4a.
 # in another unix window
 # make pipe if not exists
import os, sys
os.mkfifo('/tmp/FIFO')
def read_bytes(input_file, read_size=8192):
    while True:
        bytes_ = input_file.read(read_size)
        if not bytes_:
            break
        yield bytes_

with open("in.mov", "rb") as f:
 for bytes_ in read_bytes(f):
  in_pipe.stdin.write(bytes_)


#5.a
# FIFO reader
# First [open for read], [then open for write, then write, then close], [then read , then close]
# Note read block is there is open for write but no closure
# Note write blocks if there is no read first
import os
import errno
FIFO = 'FIFO'
print("Opening FIFO...")
with open('/tmp/FIFO','rb') as fifo:
    print("FIFO opened")
    while True:
        data = fifo.read()
        if len(data) == 0:
            print("Writer closed")
            break
        print('Read: "{0}"'.format(data))

#5.a
# FIFO writer
fifo_read = open('/tmp/FIFO', 'rb')
fifo_write = open('/tmp/FIFO', 'wb')
fifo_write.write(b"some testing data\n")
fifo_write.flush()
fifo_write.close()
# need to pass the size of the bytes written in the read function
fifo_read.read(18)
