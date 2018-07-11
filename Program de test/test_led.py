import RPi.GPIO as GPIO
import time
import threading

def turnOn(pin):
    GPIO.setmode(GPIO.BOARD)
    print("LED  Allumer")
    GPIO.output(pin,True)
    time.sleep(time_sleep_led)
    print("LED Eteindre")
    GPIO.output(pin,False)

GPIO_LEDR = 36          # LED Rouge  est branche sur la pin 36 /GPIO 16
GPIO_LEDV = 32          # LED Verte est branche sur la pin 32 /GPIO 12
time_sleep_led = 5
# Initialisation du bus GPIO
GPIO.setmode(GPIO.BOARD)            # comme la librairie MFRC522
GPIO.setwarnings(False)             # 
GPIO.setup(GPIO_LEDV, GPIO.OUT)     # Pin Led Verte
GPIO.output(GPIO_LEDV, False)       # éteindre la LED Verte
GPIO.setup(GPIO_LEDR, GPIO.OUT)     # Pin LED Rouge
GPIO.output(GPIO_LEDR, False)       # éteindre LED Rouge

i = 0
while i < 5:
    threading.Thread(name='t1',target= turnOn(GPIO_LEDV)).start()
    time.sleep(1)
    threading.Thread(name='t2',target= turnOn(GPIO_LEDR)).start()
    time.sleep(1)
    i += 1
GPIO.cleanup()