import signal as sig
from time import  sleep
from pio import ADC,Pio

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

adc = ADC(1,True)
while run:
    print(adc.read(0))
    sleep(1)
    
adc.close()
print('Done')
