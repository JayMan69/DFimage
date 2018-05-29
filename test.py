import multiprocessing,time,random
import os

def child_process(queue):
    while True:
        value = queue.get()
        pid = os.getpid()
        print ('in queue with', pid, value)

        if value == None or value == 'Q':
            print('Nothing more to process', value)
            return

        time.sleep(random.randrange(5, 11))

        print('In queue finished processing ' , pid,value, time.time())
        #return

def main():
    # jobs = []
    queue = multiprocessing.Queue()
    p = multiprocessing.Pool(2,child_process,(queue,))

    for i in range(0,3):
        print("Sending %d" % i)
        queue.put(i)

    print('In main before sleeping', time.time())
    time.sleep(3)
    print('In main after sleeping', time.time())

    for i in range(4,6):
        print("Sending %d" % i)
        queue.put(i)

    print('In main before quiting', time.time())
    # Need to put Nones for the total number of process
    queue.put('Q')
    queue.put('Q')
    queue.close()
    p.close()
    p.join()
    print('In main done', time.time())

if __name__ == "__main__":
    main()