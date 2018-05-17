from time import sleep
import os
import threading

class HLSEvent(object):
    def __init__(self):
        print('ready to parallel thread to create new HLS files ')
        thread = threading.Thread(target=run_parallel())
        thread.setDaemon(True)
        thread.start()
        print('kicked off thread')

def run_parallel ():
        # delete all files after output2.ts in static directory
        # delete all lines after output2.ts in output1.m3u8 file
        common_row = '#EXTINF:2.400000,'
        i = 0
        y = 0
        start_count = 3
        with open("./static/output1.m3u8", "a") as myfile:
            while i < 20:
                if y == 0:
                    y = y + 1
                    myfile.write(common_row + '\n')
                    new_file = 'output'+str(start_count)+ '.ts'
                    string ='copy ' + 'static\\output0.ts static\\' + new_file
                    var = os.popen(string).read()
                    myfile.write(new_file+ '\n')
                else:
                    if y == 1:
                        y = y + 1
                        myfile.write(common_row+ '\n')
                        new_file = 'output' + str(start_count) + '.ts'
                        string = 'copy ' + "static\\output1.ts static\\" + new_file
                        var = os.popen(string).read()
                        myfile.write(new_file+ '\n')
                    else:
                        y = 0
                        myfile.write(common_row+ '\n')
                        new_file = 'output' + str(start_count) + '.ts'
                        string = 'copy ' + 'static\\output2.ts static\\' + new_file
                        var = os.popen(string).read()
                        myfile.write(new_file+ '\n')

                start_count = start_count + 1
                i = i + 1
                myfile.flush()

            myfile.write('EXT-X-ENDLIST' + '\n')
            print('finished thread')

sleep(1)
new = HLSEvent()