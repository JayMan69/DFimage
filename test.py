import multiprocessing,time,random
import os

out_static_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/kvs/')
manifest_name = 'best.m3u8'

# same as _200_%06d.ts
segment_name = 'test.mkv_rawfile{:1d}.mkv'
start_number = 0
no_of_processes = 1

def test():
    process_queue = multiprocessing.Queue()
    process_queue.put(('Start', out_static_dir + segment_name))
    print('In test Starting')
    rp = run_parallel('Start', process_queue)
    #time.sleep(2)

    process_queue.put(('End','Q'))
    print('Calling run parallel 2nd time')
    rp.run('Q', process_queue)
    print ('Test done')

def save_to_S3(queue):
    # Look for files in the folder
    # As they appear push them to S3
    # If no more files, sleep and check for files again and if not found Also check queue to quit
    # TODO Need to store start in db to support more than one process concurrently
    #

    quit = False
    try_counts = 0
    first = 0
    start =  start_number

    while True and (False if (quit == True and try_counts > 2) else True):
        #logfile.write('In while loop, quit, try_counts'+str(quit)+str(try_counts))
        #print('In while loop, quit, try_counts',quit,try_counts)
        # First call gets the file format
        if first == 0:
            value1 = queue.get(block=False, timeout=.002)
            file = value1[1]
            print('--->>> Start signal with file', file)
            value = value1
            pid = os.getpid()
            first = 1

        else:
            # second call can be a None or Q
            try:
                value = queue.get(block=False, timeout=.02)
            except:
                value = ''

        if value == 'Q' :
            # check for files for a certain number of time and then quit
            time.sleep(1)
            quit = True
            #logfile.write('--->>> Quit is true')
            print('--->>> Quit signal')
            try_counts = try_counts + 1
            # print('Nothing more to process and received quit signal')
            #return


        file1 = file.format(start)
        if os.path.isfile(file1) == True:
            print('Saving file to S3', pid, file1, time.time())
            #save_file(file, DEFAULT_BUCKET, DEFAULT_S3_Folder)
            # save manifest
            #save_file(value[1], DEFAULT_BUCKET, DEFAULT_S3_Folder)
            start = start + 1
        else:
            # did not find a file. Increase try_counts
            if try_counts > 0: try_counts = try_counts + 1


    print('In queue finished processing ', pid, value, time.time())
    return

def test1(queue):
    time.sleep(10)
    print(queue.qsize())
    try:
        value1 = queue.get(block=False, timeout=.02)
    except:
        value1 = ''
        print('error1')
    print('-->queue', value1)

    try:
        value1 = queue.get(block=False, timeout=.02)
    except:
        print('error2')
        value1 = ''
    print('-->queue', value1)


class run_parallel():
    def __init__(self, initial_setup, queue_value):
        print('-->In init with', initial_setup)
        self.p = multiprocessing.Pool(no_of_processes, save_to_S3, (queue_value,))
        self.initial_setup = initial_setup

    def run(self,initial_setup, queue_value):
        print('-->In run with',initial_setup)
        if initial_setup == 'Q':
            for i in range(0, no_of_processes):
                print('--->putting new values', i)
                queue_value.put('Q')
                #print('queue put',queue.get())
            queue_value.close()
            print('closing p')
            self.p.close()
            # This will block until all sub processes are done
            print('at p.join')
            self.p.join()


if __name__ == "__main__":
    test()
