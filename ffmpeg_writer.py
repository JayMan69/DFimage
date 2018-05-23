import os
import subprocess
from subprocess import DEVNULL
import shutil,errno


class FFMPEG_VideoWriter:

    def __init__(self,logfile,w,h,static_dir,filename,segment_name,r=30):

        self.r = r
        self.logfile = logfile
        self.static_dir = static_dir
        self.filename = filename
        self.segment_name = segment_name
        output = self.static_dir + self.filename
        self.segment_name = self.static_dir + self.segment_name

        print('calling ffmpeg to convert into HLS format')
        '''
        -an: no audio
        -s: set frame-size
        -framerate: set frame-rate.
        -c:v libx264: H264 encoder for H.264
        HLS commands
        -crf: Constant Rate Factor. Set to 10 is very good
        '-g', '60': Create a key file every two seconds given 30 frames per second
        #'-vf', 'fps=fps=.9': Tried this parameter to speed up video, but does not work
        -maxrate: constrain bit rate
        -b:v constrain bit rate
        -profile:v baseline: compatibility with all older devices
        -bufsize: rate control buffer for end client player
        -pix_fmt: Quicktime supports yuv420 4:2:0 chroma
        -hls_time: 2 second segments
        -hls_list_size 0: 0 means manifest contains all segments (and not sliding frame for events)
        -t 00:30:00: Not added above, but can add before hls_commands - Cut video off at 30 minutes
        # need to investigate flags
        -y: Not used - overwrite file if exists
        -re: Read input at native framerate when reading from a web cam
        # input params 1
        '-f', 'image2pipe', '-vcodec', 'mjpeg'
        -'-vcodec', 'mjpeg':

        # input params 2
        '-f', 'rawvideo', '-vcodec','rawvideo',
        '-pix_fmt', 'rgb24': Input picture format

        # input params 3 --! did not work!!!
        # '-f', 'rawvideo',
        # '-pix_fmt' 'bgr24'
        # end
        '''
        FFMPEG_EXE = shutil.which('ffmpeg')
        # hack for IDE only
        if FFMPEG_EXE == None:
            FFMPEG_EXE = "C:\\ProgramData\\Anaconda3\\envs\\agimage\\Scripts\\ffmpeg.EXE"
            if shutil.which(FFMPEG_EXE) == None:
                print('Cannot find shutil')
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), FFMPEG_EXE)

        # changed pix_fmt from rgb24 to bgr24
        # changed -r from 30000/1001 to 1
        # commented the duplicate -r
        cmd = [FFMPEG_EXE,
               '-y',
               '-threads', '4',
               '-r','%d' %(self.r),
               '-an',
               '-s', '%dx%d' %(w, h),
               '-f', 'rawvideo',
               '-vcodec', 'rawvideo',
               '-pix_fmt', 'bgr24',
               '-i', '-',
               '-c:v','libx264',
               '-crf','30',
               #'-g', '60',
               '-r','%d' %(self.r),
               '-maxrate','900k',
               '-b:v', '900k ',
               '-profile:v', 'baseline',
               '-bufsize', '1800k',
               '-pix_fmt', 'yuv420p',
               '-hls_time', '2',
               '-hls_list_size', '0',
               '-hls_segment_filename', self.segment_name+'_200_%06d.ts',
               output]
        # instead of writing to log file we can also write to null
        #nulfp = open(os.devnull, "w")
        #"stderr": nulfp
        popen_params = {"stdout": DEVNULL,
                        "stderr": logfile,
                        "stdin": subprocess.PIPE}

        # This was added so that no extra unwanted window opens on windows
        # when the child process is created
        if os.name == "nt":
            popen_params["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        # need to check with a simple cmd like ls to see if cmd is constructed properly
        # need to pipe std err out to below
        # stderr=subprocess.STDOUT
        # try simple subprocess below
        # proc=subprocess.Popen(['cat', 'file'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        #cmd = ['dir' ,'*.txt']
        #shutil.which('frob')
        self.proc = subprocess.Popen(cmd, **popen_params)



    def write_frame(self, img_array):
        try:
            self.proc.stdin.write(img_array.tobytes())
            # for line in iter(self.proc.stdout.readline, b''):
            #     print (line)
            # self.proc.stdout.close()
            # self.proc.wait()
        except IOError as err:
            _, ffmpeg_error = self.proc.communicate()
            error = (str(err) + ("\n\nError: FFMPEG encountered "
                                 "the following error while writing file %s:"
                                 "\n\n %s" % (self.logfile , str(ffmpeg_error))))

            if b"Unknown encoder" in ffmpeg_error:

                error = error + ("\n\nThe video export "
                                 "failed because FFMPEG didn't find the specified "
                                 "codec for video encoding (%s). Please install "
                                 "this codec or change the codec when calling "
                                 "write_videofile. For instance:\n"
                                 "  >>> clip.write_videofile('myvid.webm', codec='libvpx')") % (self.codec)

            elif b"incorrect codec parameters ?" in ffmpeg_error:

                error = error + ("\n\nThe video export "
                                 "failed, possibly because the codec specified for "
                                 "the video (%s) is not compatible with the given "
                                 "extension (%s). Please specify a valid 'codec' "
                                 "argument in write_videofile. This would be 'libx264' "
                                 "or 'mpeg4' for mp4, 'libtheora' for ogv, 'libvpx for webm. "
                                 "Another possible reason is that the audio codec was not "
                                 "compatible with the video codec. For instance the video "
                                 "extensions 'ogv' and 'webm' only allow 'libvorbis' (default) as a"
                                 "video codec."
                                 ) % (self.codec, self.ext)

            elif b"encoder setup failed" in ffmpeg_error:

                error = error + ("\n\nThe video export "
                                 "failed, possibly because the bitrate you specified "
                                 "was too high or too low for the video codec.")

            elif b"Invalid encoder type" in ffmpeg_error:

                error = error + ("\n\nThe video export failed because the codec "
                                 "or file extension you provided is not a video")

            raise IOError(error)


    def close(self):
        if self.proc:
            self.proc.stdin.close()
            if self.proc.stderr is not None:
                self.proc.stderr.close()
            self.proc.wait()

        self.proc = None

class FFMPEG_VideoWriter1:

    def __init__(self,logfile,static_dir,filename,segment_name):


        self.logfile = logfile
        self.static_dir = static_dir
        self.filename = filename
        output = self.static_dir + self.filename
        self.segment_name = self.static_dir + segment_name

        print('calling ffmpeg to convert into mkv format')
        '''
        -y: Not used - overwrite file if exists
        -an: no audio
        -s: set frame-size
        -framerate: set frame-rate.
        -c:v libx264: H264 encoder for H.264
        # need to investigate flags

        -re: Read input at native framerate when reading from a web cam
        '''
        FFMPEG_EXE = shutil.which('ffmpeg')
        # hack for IDE only
        if FFMPEG_EXE == None:
            FFMPEG_EXE = "C:\\ProgramData\\Anaconda3\\envs\\agimage\\Scripts\\ffmpeg.EXE"
            if shutil.which(FFMPEG_EXE) == None:
                print('Cannot find shutil')
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), FFMPEG_EXE)

        # changed pix_fmt from rgb24 to bgr24
        # changed -r from 30000/1001 to 1
        # commented the duplicate -r
        cmd = [FFMPEG_EXE,
               '-y',
               '-an',
               '-f', 'rawvideo',
               '-vcodec', 'rawvideo',
               #'-pix_fmt', 'bgr24',
               '-pix_fmt','yuv420p',
               # note its -r not r
               #'-r' , '25',
               '-s' ,'640x480',
               '-i', '-',
               #'-r', '25',
               '-c:v','libx264',
               '-maxrate', '900k',
               '-b:v', '900k ',
               '-profile:v', 'baseline',
               '-bufsize', '1800k',
               '-pix_fmt', 'yuv420p',
               '-hls_time', '2',
               '-hls_list_size', '0',
               '-hls_segment_filename', self.segment_name + '_200_%06d.ts',
               output]
        # instead of writing to log file we can also write to null
        #nulfp = open(os.devnull, "w")
        #"stderr": nulfp
        popen_params = {"stdout": DEVNULL,
                        "stderr": logfile,
                        "stdin": subprocess.PIPE}

        # This was added so that no extra unwanted window opens on windows
        # when the child process is created
        if os.name == "nt":
            popen_params["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        # need to check with a simple cmd like ls to see if cmd is constructed properly
        # need to pipe std err out to below
        # stderr=subprocess.STDOUT
        # try simple subprocess below
        # proc=subprocess.Popen(['cat', 'file'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        #cmd = ['dir' ,'*.txt']
        #shutil.which('frob')
        self.proc = subprocess.Popen(cmd, **popen_params)



    def write_frame(self, img_array):
        try:
            self.proc.stdin.write(img_array)
            # for line in iter(self.proc.stdout.readline, b''):
            #     print (line)
            # self.proc.stdout.close()
            # self.proc.wait()
        except IOError as err:
            _, ffmpeg_error = self.proc.communicate()
            error = (str(err) + ("\n\nError: FFMPEG encountered "
                                 "the following error while writing file %s:"
                                 "\n\n %s" % (self.logfile , str(ffmpeg_error))))

            if b"Unknown encoder" in ffmpeg_error:

                error = error + ("\n\nThe video export "
                                 "failed because FFMPEG didn't find the specified "
                                 "codec for video encoding (%s). Please install "
                                 "this codec or change the codec when calling "
                                 "write_videofile. For instance:\n"
                                 "  >>> clip.write_videofile('myvid.webm', codec='libvpx')") % (self.codec)

            elif b"incorrect codec parameters ?" in ffmpeg_error:

                error = error + ("\n\nThe video export "
                                 "failed, possibly because the codec specified for "
                                 "the video (%s) is not compatible with the given "
                                 "extension (%s). Please specify a valid 'codec' "
                                 "argument in write_videofile. This would be 'libx264' "
                                 "or 'mpeg4' for mp4, 'libtheora' for ogv, 'libvpx for webm. "
                                 "Another possible reason is that the audio codec was not "
                                 "compatible with the video codec. For instance the video "
                                 "extensions 'ogv' and 'webm' only allow 'libvorbis' (default) as a"
                                 "video codec."
                                 ) % (self.codec, self.ext)

            elif b"encoder setup failed" in ffmpeg_error:

                error = error + ("\n\nThe video export "
                                 "failed, possibly because the bitrate you specified "
                                 "was too high or too low for the video codec.")

            elif b"Invalid encoder type" in ffmpeg_error:

                error = error + ("\n\nThe video export failed because the codec "
                                 "or file extension you provided is not a video")

            raise IOError(error)


    def close(self):
        if self.proc:
            self.proc.stdin.close()
            if self.proc.stderr is not None:
                self.proc.stderr.close()
            self.proc.wait()

        self.proc = None
