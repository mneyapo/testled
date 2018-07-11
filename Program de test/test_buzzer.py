import RPi.GPIO as GPIO
import time
import threading

#A bUZZER (5v) il est mis en 3.3v PIN 17
GPIO_buzzer = 7
time_sleep_buzzer =1

def buzzer_on():
    GPIO.output(GPIO_buzzer,0) # inactif = buzzer
    time.sleep(time_sleep_buzzer)
    GPIO.output(GPIO_buzzer,1)
    
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(GPIO_buzzer,GPIO.OUT)
GPIO.output(GPIO_buzzer,True)

i = 0
while i < 5:
    print('.',end="")
    threading.Thread(name='t0',target= buzzer_on()).start()
    time.sleep(1)
    i += 1
GPIO.cleanup()