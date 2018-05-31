from multiprocessing import Process
from multiprocessing import Queue
import time

class Sentinel(object): pass

class EchoProcess(Process):

    def __init__(self, iQ):
        Process.__init__(self)
        print ('in here')
        self.iQ = iQ

    def run(self):
        test = self.iQ.get
        for istring in iter(test, 'Q'):
            print('reading in child',istring)
            pass

        print("exited")




if __name__ == "__main__":
    iQ = Queue()
    echoProcess = EchoProcess(iQ)
    echoProcess.start()
    iQ.put(10)
    iQ.put(10)
    for i in range (0,3):
        print ('put in queue', i)
        time.sleep(5)
        iQ.put(i)
    print('put in last value into queue','Q')
    iQ.put('Q')
    echoProcess.join()