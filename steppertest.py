# steppertest.py
# written by Roger Woollett
# tested with python 3 

import signal as sig
import threading as th
from time import  sleep

from pio import Stepper,Pio

# comment out this line if running
# on the pi with the ADC otherwise put
# name or ip address of the pi
Pio.host = 'Gimli'

run = True

# Thread class to run a single stepper
class StepperThread(th.Thread):
    def __init__(self,stepper):
        th.Thread.__init__(self)
        self.stepper = stepper
        self.event = th.Event()
        self.event.clear()
        self.go = True
        
    def run(self):
        while self.go:
            self.event.wait()
            self.stepper.steps(*self.args)
            self.event.clear()
            # TODO signal completion
            
        self.stepper.close()
        
    def steps(self,count,delay,forward = True):
    # cal to set parameters for one set of steps
        self.args=(count,delay,forward)
        self.event.set()
        
    def is_ready(self):
    # call to see if thread is busy
        return not self.event.is_set()
    
    def abort_steps(self):
    # call to abort steps
        self.stepper.abort_steps()
        
    def end(self):
    # call to end thread
        self.go = False
        self.event.set()
        
def on_exit(a,b):
    global run
    run = False
    
sig.signal(sig.SIGINT,on_exit)
print("Ctrl+C to exit")

# Thread 1
# stepper object see pio.py for constructor params
st1 = Stepper(23,24)
# thread object
th1 = StepperThread(st1)
th1.start()

# parameters for a sequence of calls to steps
th1_seq = ((50,0.02,True),(30,0.05,False),(40,0.01,True))
th1_num = len(th1_seq)
th1_index = 0

# thread 2
st2 = Stepper(14,15)
th2 = StepperThread(st2)
th2.start()
th2_seq = ((100,0.01,False),(30,0.3,True),(40,0.01,False))
th2_num = len(th2_seq)
th2_index = 0


while run and (th1_index < th1_num) or (th2_index < th2_num):
    if(th1.is_ready() and th1_index < th1_num):
        th1.steps(*th1_seq[th1_index])
        th1_index += 1
    
    if(th2.is_ready() and th2_index < th2_num):
        th2.steps(*th2_seq[th2_index])
        th2_index += 1

    try:
        sleep(0.1)
    except:
        pass
    
    
th1.end()
th2.end()

while th1.is_alive() or th2.is_alive():
    sleep(0.1)

print('Done')
