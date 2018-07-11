from datetime import *
# requires RPi_I2C_driver.py
import RPi_I2C_driver
from time import *
import RPi.GPIO as GPIO
import smbus
import time
import datetime
import threading


GPIO_LEDR = 36          # LED Rouge  est branche sur la pin 36 /GPIO 16
GPIO_LEDV = 32          # LED Verte est branche sur la pin 32 /GPIO 12
GPIO_relais = 40        # Relais est branche sur la pin 40 / GPIO21
GPIO_buzzer = 7         # Buzzer est Branche sur la pin 7 /GPIO 4
#********************************************************

#********************************************************
# Délais d'Attente
time_boucle = 1         # ??
time_sleep_led = 2     # Durée d'affichage de la LED dans le thread
time_sleep_relay = 1    # Durée d'activation du Relais
time_sleep_buzzer = 1
#*******************************************************
#********************************************************

#********************************************************
# Récupération de la Date et l'Heure du Raspberry au format AAAA-MM-JJ HH:mm:SS
def get_rpi_time():
    strtoday= datetime.datetime.utcnow()
    rpitime=strtoday.strftime("%Y-%m-%d %H:%M:%S")
    return rpitime
#********************************************************
def msg(L1,L2): # Affichage Message sur 2 lignes, et report sur Console **
    mylcd.lcd_clear()
    mylcd.lcd_display_string(L1, 1)
    mylcd.lcd_display_string(L2, 2)
    print("LCD:",L1,"|",L2)
#**********************************************************

#********************************************************
# Initialisation du bus GPIO
GPIO.setmode(GPIO.BOARD)            # comme la librairie MFRC522
GPIO.setwarnings(False)             # 
GPIO.setup(GPIO_relais,GPIO.OUT, initial=GPIO.HIGH)
GPIO.output(GPIO_relais, True)      # éteindre le Relais
GPIO.setup(GPIO_buzzer,GPIO.OUT)
GPIO.output(GPIO_buzzer,True)       # éteindre buzzer
GPIO.setup(GPIO_LEDV, GPIO.OUT)     # Pin Led Verte
GPIO.output(GPIO_LEDV, False)       # éteindre la LED Verte
GPIO.setup(GPIO_LEDR, GPIO.OUT)     # Pin LED Rouge
GPIO.output(GPIO_LEDR, False)       # éteindre LED Rouge
#********************************************************

#********************************************************
# Pour allumer, attendre et éteindre une LED (pin)
def turnOn(pin):
    
    if pin == 32:
        pname = "VERT"
    else:
        pname = "ROUGE"
        
    GPIO.setmode(GPIO.BOARD)
    msg("LED "+pname,"Allumer")
    GPIO.output(pin,True)
    time.sleep(time_sleep_led)
    msg("LED "+pname,"Eteindre")
    GPIO.output(pin,False)
#********************************************************
continue_reading =True
#********************************************************
def end_read(signal,frame):
    global continue_reading
    print ("\nLecture terminée")
    msg("MACHINE ARRETEE", "ESSAYEZ + TARD")
    continue_reading = False
    rdr.cleanup()
    GPIO.cleanup()
#********************************************************
# Pour déclencher le relais
def declencherelay():
    GPIO.output(GPIO_relais, GPIO.LOW)    # Allumer
    msg("Declenche","relais Allumer")
    time.sleep(time_sleep_relay)
    GPIO.output(GPIO_relais, GPIO.HIGH)  
    #GPIO.output(GPIO_relais, GPIO.LOW)      # Eteindre
    msg("Declenche","relais Eteindre")
    time.sleep(time_sleep_relay)
    
def buzzer_on():
    msg("Buzzer","Allumer")
    GPIO.output(GPIO_buzzer,0) # inactif = buzzer
    time.sleep(time_sleep_buzzer)
    msg("Buzzer","Eteindre")
    GPIO.output(GPIO_buzzer,1)
#********************************************************
# Initialiser le LCD
mylcd = RPi_I2C_driver.lcd()
# test 2
msg("RPi I2C test",get_rpi_time())
time.sleep(2)
print("Début :")
i = 0
try:
    
    if True:
        # Boucle principale
        while i < 1:
            # Afficher un point à chaque tourne
            print(".", end="")
            #Declenchement relais
            threading.Thread(name='t0',target= declencherelay()).start()
            #Allumer la Led Verte
            threading.Thread(name='t1',target= turnOn(GPIO_LEDV)).start()
            time.sleep(1)
            threading.Thread(name='t2',target= turnOn(GPIO_LEDR)).start()
            time.sleep(1)
            threading.Thread(name='t3',target= buzzer_on()).start()
            time.sleep(1)
            i +=1
           
    GPIO.cleanup()
except:
    GPIO.cleanup()
    msg("PROGRAM ARRETER","ESSAYER + TARD")
    
