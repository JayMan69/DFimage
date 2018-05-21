import shutil,os
import subprocess,shutil

test = shutil.which("C:\\ProgramData\\Anaconda3\\envs\\agimage\\Scripts\\ffmpeg.EXE")
#cmd = ["C:\\ProgramData\\Anaconda3\\envs\\agimage\\Scripts\\ffmpeg.EXE" , "-h"]

#subprocess.Popen (cmd)


static = (os.path.join(os.path.dirname(os.path.realpath(__file__)),'static/'))
file = static +'output0.ts1'
print(os.path.isdir(static))
print(os.path.isfile(file))