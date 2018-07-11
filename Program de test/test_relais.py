import RPi.GPIO as GPIO
import time

GPIO_relais = 40
time_sleep_relay =3

GPIO.setmode(GPIO.BOARD)            # comme la librairie MFRC522    #
GPIO.setup(GPIO_relais,GPIO.OUT, initial=GPIO.HIGH)
# GPIO.output(GPIO_relais,0)
i = 0
while i < 5:
    GPIO.output(GPIO_relais,0) # inactif = déclechement
    ##GPIO.cleanup()
    time.sleep(1)
    GPIO.output(GPIO_relais,1) # actif = arrêt
    time.sleep(1)
    i += 1
GPIO.cleanup()
##print(state)
