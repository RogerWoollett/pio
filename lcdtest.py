import signal as sig
from time import  sleep

from pio import LCD,Pio

# comment out this line if running
# on the pi with the ADC otherwise put
# name or ip address of the pi
Pio.host = 'Gimli'

run = True

def on_exit(a,b):
    global run
    run = False
    
sig.signal(sig.SIGINT,on_exit)
print("Ctrl+C to exit")

lcd = LCD(23,24,25,26,27,22)
lcd.set_cursor(1,3)
lcd.send_string('Hello world')

while run:
    sleep(1)
    
lcd.close()
print('Done')
