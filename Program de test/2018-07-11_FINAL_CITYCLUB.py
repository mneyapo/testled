#!/usr/bin/python3
# -*- coding: utf8 -*-
# System module

from datetime import *
import RPi.GPIO as GPIO
# import MFRC522
from pirc522 import RFID
import smbus
import time
import datetime
import MySQLdb
import threading
import sys
import requests
import json
import socket
import signal
import os
import re
clear = lambda:os.system('clear')
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#********************************************************
# Variables Globales
rpiname = str(socket.gethostname())     # Nom RPI
societe = "CITY_CLUB"                   # Client
state=""                                # Etat de la Carte
Can_Try_Offline_Upload = False          # Permet de savoir si on peut tenter des remontées d'informations offline
LAST_MSG = ""                           # Message qui sera affiché le dernier
next_action = ""                        # Action a effectuer ensuite
Card_Init_Status = ""                   # Etat de la Carte au moment de la lecture de l'UID
last_visit = ""                         # Dernière visite enregistrée sur la carte
bOK = True                              # pour les traitements Go / no Go
boucle_attente = False                  # utilisé pour attendre que la Carte soit retirée
boucle_compteur = 120                     # utilisé comme compteur de passages dans la boucle principale
rbnom = ""                              # Nom du Raspberry installé dans le tourniquet
url_ping_CC = ""                        # URL du ping CityClub
timeout_ping = 0                        # Timeout sur le Ping CityClub
url_WS = ""                             # URL du WebService CityClub
url_WS_tm = 0                           # Timeout sur le WebService CityClub
url_yapo_ping = ""                      # URL du Ping YAPO
last_UID = []                           # dernier UID lu
last_UID_datetime = datetime.datetime.utcnow()  # date et heure du dernier UID lu
last_message_l1 = ""                    # Dernier message sur le LCD, ligne 1, qui pourra être réaffiché
last_message_l2 = ""                    # Dernier message sur le LCD, ligne 2, qui pourra être réaffiché
Est_Carte = False
Est_Auth = False
tag_uid = []
data_bloc = []
#********************************************************

#********************************************************
# Carte RFID
# Clefs d'authentification
key_public    = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]      # Clé publique
key_YAPO      = [0x59,0x61,0x50,0x6F,0x54,0x74]      # clé privée YAPO
key_CityClub  = [0x43,0x69,0x54,0x79,0x43,0x6C]      # clé privée CityClub
Sector_Key_CC = [0x43,0x69,0x54,0x79,0x43,0x6C,0xFF,0x07,0x80,0x69,0x43,0x69,0x54,0x79,0x43,0x6C] # ce qu'il faut écrire dans le secteur d'authentification pour protéger la carte avec la clef privée CityClub
# Bloc1
B1S4 = 4            # FirstName
B1S5 = 5            # LastName
B1S7 = 7            # Clef d'Authentification
# Bloc2
B2S8 = 8            # Date Limite d'Abonnement
B2S11 = 11          # Clef d'Authentification
# Bloc3
B3S12 = 12          # Last Visit (Date dernier passage)
B3S15 = 15          # Clef d'Authentification
# Pour savoir si une carte est insérée
Card_Insert = 0     # carte détectée (pour boucler tant que la carte n'a pas été retirée)
#********************************************************

#********************************************************
# Bus GPIO
# LED
GPIO_LEDR = 36          # LED Rouge  est branche sur la pin 36 /GPIO 16
GPIO_LEDV = 32          # LED Verte est branche sur la pin 32 /GPIO 12
GPIO_relais = 40        # Relais est branche sur la pin 40 / GPIO21
GPIO_buzzer = 7         # Buzzer est Branche sur la pin 7 /GPIO 4
#********************************************************

#********************************************************
# Délais d'Attente
time_boucle = 1         # ??
time_sleep_led = 5      # Durée d'affichage de la LED dans le thread
time_sleep_relay = 1    # Durée d'activation du Relais
time_sleep_buzzer = 1     # Durée d'activation du Buzzer
#********************************************************

#********************************************************
# Afficheur LCD via le bus I2C
I2C_ADDR  = 0 # pour test 0x27 et  0x3f pour city club
LCD_WIDTH = 16   # Maximum characters per line
LCD_CHR = 1 # Mode - Sending data
LCD_CMD = 0 # Mode - Sending command
LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line
LCD_LINE_3 = 0x94 # LCD RAM address for the 3rd line
LCD_LINE_4 = 0xD4 # LCD RAM address for the 4th line
LCD_BACKLIGHT  = 0x08  # On
ENABLE = 0b00000100 # Enable bit
E_PULSE = 0.0005 # Timing constants
E_DELAY = 0.0005 # Timing constants
#********************************************************

#********************************************************
# Initialisation du bus GPIO
GPIO.setmode(GPIO.BOARD)            # comme la librairie MFRC522
GPIO.setwarnings(False)             #setwarnings to False
GPIO.setup(GPIO_relais, GPIO.OUT, initial=GPIO.HIGH)   # Pin Relais
GPIO.output(GPIO_relais, True)      # éteindre le Relais
GPIO.setup(GPIO_buzzer,GPIO.OUT, initial=GPIO.HIGH) # Pin Buzzer #A bUZZER (5v) il est mis en 3.3v PIN 17
GPIO.output(GPIO_buzzer,True)       # éteindre Buzzer
GPIO.setup(GPIO_LEDV, GPIO.OUT)     # Pin Led Verte
GPIO.output(GPIO_LEDV, False)       # éteindre la LED Verte
GPIO.setup(GPIO_LEDR, GPIO.OUT)     # Pin LED Rouge
GPIO.output(GPIO_LEDR, False)       # éteindre LED Rouge
#********************************************************

#********************************************************
# Pour allumer, attendre et éteindre une LED (pin)
def turnOn(pin):
    GPIO.setmode(GPIO.BOARD)
    GPIO.output(pin,True)
    time.sleep(time_sleep_led)
    GPIO.setmode(GPIO.BOARD) 
    GPIO.output(pin,False)
#********************************************************

#********************************************************
# Pour déclencher le relais
def declencherelay():
    GPIO.output(GPIO_relais, False)     # Allumer
    # GPIO.output(GPIO_relais, True)    # Allumer
    time.sleep(time_sleep_relay)        # Attendre
    # GPIO.output(GPIO_relais, False)   # Eteindre
    GPIO.output(GPIO_relais, True)      # Eteindre
#********************************************************

#*********************************************************
# Pour déclencher buzzer
def buzzer_on():
    GPIO.output(GPIO_buzzer,0) # inactif = buzzer
    time.sleep(time_sleep_buzzer)
    GPIO.output(GPIO_buzzer,1)
#********************************************************

#*********************************************************    
def lcd_init(): # Initialisation LCD ************************************
    lcd_byte(0x33,LCD_CMD) # 110011 Initialise
    lcd_byte(0x32,LCD_CMD) # 110010 Initialise
    lcd_byte(0x06,LCD_CMD) # 000110 Cursor move direction
    lcd_byte(0x0C,LCD_CMD) # 001100 Display On,Cursor Off, Blink Off 
    lcd_byte(0x28,LCD_CMD) # 101000 Data length, number of lines, font size
    lcd_byte(0x01,LCD_CMD) # 000001 Clear display
    time.sleep(E_DELAY)
def lcd_byte(bits, mode): # Send byte to data pins, bits = the data, mode = 1 for data, 0 for command
    bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
    bits_low = mode | ((bits<<4) & 0xF0) | LCD_BACKLIGHT
    bus.write_byte(I2C_ADDR, bits_high) # High bits
    lcd_toggle_enable(bits_high)
    bus.write_byte(I2C_ADDR, bits_low) # Low bits
    lcd_toggle_enable(bits_low)
def lcd_toggle_enable(bits): # LCD Toggle Enable **************************************
    time.sleep(E_DELAY)
    bus.write_byte(I2C_ADDR, (bits | ENABLE))
    time.sleep(E_PULSE)
    bus.write_byte(I2C_ADDR,(bits & ~ENABLE))
    time.sleep(E_DELAY)
def lcd_string(message,line): # Affichage Message sur une Ligne ************************
    message = message.ljust(LCD_WIDTH," ") # Send string to display
    lcd_byte(line, LCD_CMD)
    for lcd_i in range(LCD_WIDTH):
        lcd_byte(ord(message[lcd_i]),LCD_CHR)
def msg(L1,L2): # Affichage Message sur 2 lignes, et report sur Console **
    global last_message_l1
    global last_message_l2
    last_message_l1 = L1
    last_message_l2 = L2
    lcd_string(L1,LCD_LINE_1)
    lcd_string(L2,LCD_LINE_2)
    print("LCD:",L1,"|",L2)
#**********************************************************


#********************************************************
# Récupération des Paramètres dans la base MySQL
def get_param(Param_N):
    try:
        db = MySQLdb.connect("127.0.0.1", "yapo", "pipi", "rpi")
        curs=db.cursor()
        curs.execute("SELECT Param_Valeur FROM Parametre Where Param_Nom='%s'"% Param_N)
        results = curs.fetchall()
        for row in results:
            Param_Valeur = row[0]
        db.close()
    except Exception as e:
        print(e)
        db.close()
    return  Param_Valeur
#********************************************************

#********************************************************
# Récupération de la Date et l'Heure du Raspberry au format AAAA-MM-JJ HH:mm:SS
def get_rpi_time():
    strtoday= datetime.datetime.utcnow()
    rpitime=strtoday.strftime("%Y-%m-%d %H:%M:%S")
    return rpitime
#********************************************************

#********************************************************
def h2str(entree):
    sortie=str(chr(entree))
    return sortie
#********************************************************

#********************************************************
def read_card(backData):
    Datatemp = ""
    c =0
    while (c<16):
        if(backData[c]!=0):
            try:
                Datatemp=Datatemp+h2str(backData[c])
            except Exception as e:
                print(e)
        c=c+1
    #print("\n")
    return Datatemp
#********************************************************

#********************************************************
def write_data(sdata):
    data = []
    strx=sdata
    for c in strx:
        if (len(data)<16):
            data.append(int(ord(c)))
    while(len(data)!=16):
        data.append(0)
    return data
#********************************************************

#********************************************************
def from_card(date_time):
    backData=date_time[0:4]+"-"+date_time[4:6]+"-"+date_time[6:8]+date_time[8:11]+":"+date_time[11:13]+":"+date_time[13:15]
    return backData
#********************************************************

#*******************************************************
def Date_Comparison(DATE_VALID):
    DATE_DAY=strtoday.strftime("%Y-%m-%d")
    if DATE_VALID >= DATE_DAY:
        bOkString="OK"
    else:
        if DATE_VALID != "":
            bOkString="STOP X04"
        else:
            bOkString="STOP X07"
    return bOkString
#*******************************************************

#*******************************************************
# Envoi d'un ping vers le serveur Yapo
def Ping_Yapo():
    global url_yapo_ping    # URL du Ping YAPO
    try:
        my_req = requests.get(url_yapo_ping, verify = True, timeout = 1) # Timeout 1 seconde
        if my_req.status_code != 200:
            print("Echec, code : ", end="")
            print(my_req.status_code)
        else:
            print(my_req.text) # OK : + Date et Heure du serveur YAPO
    except Exception as e:
        print("Exception : ", end="")
        print(e)
#********************************************************

#********************************************************
# Envoi d'un ping vers le serveur 
def Ping_Local_CityClub():
    global url_ping_CC              # url du Ping CityClub
    global rbnom                    # le Nom local du RPI
    global Can_Try_Offline_Upload   # Permet de savoir s'il faut faire des remontées d'information Offline
    my_post_data = '{"idreader":"' + rbnom + '","mode":"ping"}' # POST data envoyé au Ping
    my_headers = {'Content-Type':'application/json','Accept':'application/json'}
    try:
        requests.packages.urllib3.disable_warnings()
        req=requests.post(url_ping_CC, data = my_post_data, headers = my_headers, verify = False, timeout=0.5) # timeout 1/2 seconde
        if req.status_code != 200:
            Can_Try_Offline_Upload = False
            state="offline"
            print("Echec, code : ", end="")
            print(req.status_code)
            return state, get_rpi_time()
        else:
            state="online"
            my_reponse_json = json.loads(req.text)
            ping_reply_datetime = my_reponse_json['currentdatetime'] # Date et Heure retourné par le ping CC
            Can_Try_Offline_Upload = True # autoriser les remontées d'information
            print("OK : ", ping_reply_datetime)
            return state, ping_reply_datetime
    except Exception as e:
        Can_Try_Offline_Upload = False
        state="offline"
        print("Echec, Exception : ", end = "")
        print(e)
        return state,get_rpi_time()
#********************************************************

#********************************************************
def Appel_Web_Service(json_data):
    global url_WS
    global url_WS_tm
    global Can_Try_Offline_Upload   # Permet de savoir s'il faut faire des remontées d'information Offline
    headers = {'Content-Type':'application/json','Accept':'application/json'}   
    try:
        requests.packages.urllib3.disable_warnings()
        r=requests.post(url_WS, data = json_data, headers = headers, verify = False, timeout = url_WS_tm)
        if r.status_code != 200:
            Can_Try_Offline_Upload = False
            print("Failed to post data to server")
            mode = "pas200"
            return r,mode
        else:
            mode ="online"
            Can_Try_Offline_Upload = True
            return r,mode          
    except Exception as e:
        Can_Try_Offline_Upload = False
        r =""
        mode = "exception"
        return r,mode
#********************************************************

#********************************************************
def String_replace(time_temp):
    time_temp=time_temp.replace('-','')
    time_temp=time_temp.replace(':','')
    return time_temp
#********************************************************

#*****************************************************************
def change_date_format(dt):
        return re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3-\\2-\\1', dt)
#*****************************************************************
    
#********************************************************
def mise_a_jour_carte(Date_visite,sectorBlock,key):
    bOK = True
    date_a_ecrire=write_data(Date_visite)
    # print("date a ecrire : ", Date_visite)
    try:
        status = MIFAREReader.MFRC522_Auth(MIFAREReader.PICC_AUTHENT1A, sectorBlock, key, uid)
        if status == MIFAREReader.MI_OK:
            try:
                MIFAREReader.MFRC522_Write(sectorBlock,  date_a_ecrire)
            except:
                bOK = False
        print("Write lastvisit B3S12 : ", bOK, date_a_ecrire)
    except Exception as e:
        print(e)
#********************************************************
        
#********************************************************
def Traitement_OK_STOP(res):
    if res == 'OK':
        print("Led Verte - ", end = "")       
        t2 = threading.Thread(name='t2',target=turnOn, args=(GPIO_LEDV,)).start()        
        print("Relais")      
        t1 = threading.Thread(name='t1',target= declencherelay).start()       
    else:
        print("Led Rouge")
        t3 = threading.Thread(name='t3',target=turnOn, args=(GPIO_LEDR,)).start()
#********************************************************

#********************************************************
def select_COUNT():
    try:
        fcount =0
        db = MySQLdb.connect("127.0.0.1", "yapo", "pipi", "rpi")
        curs=db.cursor()
        sql = "SELECT count(*) FROM CityClub WHERE Est_Envoye='NON' AND A_Remonter= 'OUI'"
        curs.execute(sql)
        results = curs.fetchall()
        for row in results:
            fcount = row[0]
        db.close()
    except:
        print("Exception while MYSQL Connection")
        print(err)
        db.close()
    return fcount
#********************************************************

#********************************************************
def insert_passage(host,uidcarte,Nom,Prenom,Datefin,rpitimes,dvisit,A_Envoyer,A_remonter,Result):
    try:
        db = MySQLdb.connect("127.0.0.1", "yapo", "pipi", "rpi")
        curs=db.cursor()
        query="INSERT INTO CityClub SET idreader='%s', mode='offline', uid='%s', firstname='%s', lastname='%s', enddate='%s', rpitime='%s',newvisit='%s' ,	Est_Envoye= '%s',A_Remonter= '%s',Result_ws= '%s'" % (host,uidcarte,Nom,Prenom,Datefin,rpitimes,dvisit,A_Envoyer,A_remonter,Result)
        print("query: ",query)
        curs.execute(query)
        print("log a bien été ajouté !'")
        db.commit()
        db.close()
    except MySQLdb.Error as err:
        print("Exception while MYSQL Connection")
        print(err)
        db.close()
#********************************************************
        
#********************************************************
def update_passage(ServerID):
    try:
        db = MySQLdb.connect("127.0.0.1", "yapo", "pipi", "rpi")
        curs=db.cursor()
        curs.execute("UPDATE CityClub SET Est_Envoye='OUI' WHERE id='%s'" % ServerID)
        db.commit()  # accept the changes
        state="Envoyée"
    except MySQLdb.Error as err:
        state="Exception while MYSQL Connection"
        print(err)
        db.close()
    finally:
        curs.close()
        db.close()
    return state
#********************************************************

#********************************************************
def select__passage():
    try:
        db = MySQLdb.connect("127.0.0.1", "yapo", "pipi", "rpi")
        curs=db.cursor()
        sql = "SELECT * FROM CityClub WHERE Est_Envoye='NON' AND A_Remonter='OUI' ORDER BY newvisit ASC LIMIT 1"
        curs.execute(sql)
        results = curs.fetchall()
        for row in results:
            fid = row[0]
            carte_da ='{"idreader":"'+row[1]+'","uid":"'+row[3]+'","mode":"'+row[2]+'","rpitime":"'+row[7]+'","lastvisit":"'+row[8]+'","resultacb":"'+row[11]+'"}'
        print(carte_da)
        response=Appel_Web_Service(carte_da)
        print("response",response)
        if response !="":
            st=update_passage(fid)
            print(st)
        time.sleep(1)
    except MySQLdb.Error as err:
        print("Exception while MYSQL Connection")
        print(err)
        db.close()
    except Exception as e:
        print("Error Connection",e)
#********************************************************

#********************************************************
def traitement_post_online():
    count = select_COUNT()
    if count !=0:
        print("Nombre File D'attente:",count)
        select__passage()
#********************************************************

#********************************************************
def recup_date_val(dlv): # autre method equivalante read_card()+h2str
    Date_TEMP=""
    Date_TEMP_OUT=""    
    c= 0
    while (c<len(dlv)):
        if(dlv[c]!=0):
            try:
                Date_TEMP=str(chr(dlv[c]))
                Date_TEMP_OUT=Date_TEMP_OUT+Date_TEMP
            except :
                print(" Contenu Illisible")
        c=c+1
    return Date_TEMP_OUT
#********************************************************


#-------------------------------------------------------
def Write_lastname_firstname_to_Card(lastname,firstname, current_UID):
# Ecrit le lastname dans le secteur B1S4 et le firstname dans le secteur B1S5
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    # first try with Public key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST PB")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST PB 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD PB ...")
            # print("UID PB ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT PB ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B1S4, key_public, my_UID)
                        # print("AUTH A PB ...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A PUBLIC B1S4 OK")
    # second try with Public key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD CC ...")
            # print("UID CC ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT CC ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B1S4, key_CityClub, my_UID)
                        # print("AUTH A CC ...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A CITYCLUB B1S4 OK")
    # third try with YAPO key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD YP ...")
            # print("UID YP ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT YP ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B1S4, key_YAPO, my_UID)
                        # print("AUTH A YP ...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A YAPO B1S4 OK")
    # Ecrire les blocs et le trailer
    if not (E_Carte and E_Auth):
        print("Echec Auth B1S4")
        Est_Erreur = True
    else:
        # Ecrire firstname B1S4
        # (Est_Erreur, my_data) = rdr.read(B1S4)
        if True: # not Est_Erreur:
            # print("B1S4 avant : ", str(my_data))
            my_data = write_data(firstname)
            # print("MY DATA : ", str(my_data))
            Est_Erreur = rdr.write(B1S4, my_data)
            if not Est_Erreur:
                pass
                # print("   OK - B1S4") # : ", str(rdr.read(B1S4)))
            else:
                print("Erreur Ecriture B1S4")       
        # Ecrire Lastname B1S5
        if not Est_Erreur:
            # (Est_Erreur, my_data) = rdr.read(B1S5)
            if True: # not Est_Erreur:
                # print("B1S5 avant : ", str(my_data))
                my_data = write_data(lastname)
                # print("MY DATA : ", str(my_data))
                Est_Erreur = rdr.write(B1S5, my_data)
                if not Est_Erreur:
                    pass
                    # print("   OK - B1S5") #  : ", str(rdr.read(B1S5)))
                else:
                    print("   Erreur Ecriture B1S5")      
        # Ecrire clef CC dans le Trailer
        if not Est_Erreur:
            # (Est_Erreur, my_data) = rdr.read(B1S7)
            if True: #not Est_Erreur:
                # print("B1S7 avant : ", str(my_data))
                my_data = Sector_Key_CC
                # print("MY DATA : ", str(my_data))
                Est_Erreur = rdr.write(B1S7, my_data)
                if not Est_Erreur:
                    pass
                    # print("   OK - B1S7")
                else:
                    print("   Erreur Ecriture B1S7") 
    # Conclure
    rdr.stop_crypto()
    return Est_Erreur
#-------------------------------------------------

#-------------------------------------------------------
def Read_lastname_firstname_from_Card(current_UID):
# Ecrit le lastname dans le secteur B1S4 et le firstname dans le secteur B1S5
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    my_lastname = ""
    my_firstname = ""
    # try auth with CC key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST CC")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST CC 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD CC ...")
            # print("UID CC ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT CC ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B1S4, key_CityClub, my_UID)
                        # print("AUTH A CC...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A CITYCLUB B1S4 OK")
    # Lire
    if not (E_Carte and E_Auth):
        print("Echec Auth B1S4")
        Est_Erreur = True
    else:
        # Lire Firstname B1S4
        (Est_Erreur, my_data) = rdr.read(B1S4)
        if not Est_Erreur:
            my_firstname = read_card(my_data)
        # Lire Lastname B1S5
        if not Est_Erreur:
            (Est_Erreur, my_data) = rdr.read(B1S5)
            if not Est_Erreur:
               my_lastname = read_card(my_data)
    # Conclure
    rdr.stop_crypto()
    return Est_Erreur, my_lastname, my_firstname
#-------------------------------------------------


#-------------------------------------------------------
def Write_SubScription_End_Date_to_Card(subscription_end_date, current_UID):
# Ecrit la Date de Fin d'abonnement dans le secteur B2S8
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    # first try with Public key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST PB")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST PB 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD PB ...")
            # print("UID PB ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT PB ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B2S8, key_public, my_UID)
                        # print("AUTH A PB ...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A PUBLIC B2S8 OK")
    # second try with Public key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD CC ...")
            # print("UID CC ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT CC ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B2S8, key_CityClub, my_UID)
                        # print("AUTH A CC ...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A CITYCLUB B2S8 OK")
    # third try with YAPO key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD YP ...")
            # print("UID YP ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT YP ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B2S8, key_YAPO, my_UID)
                        # print("AUTH A YP ...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A YAPO B2S8 OK")
    # Ecrire les blocs et le trailer
    if not (E_Carte and E_Auth):
        print("Echec Auth B2S8")
        Est_Erreur = True
    else:
        # Ecrire Subscription End Date dans B2S8
        # (Est_Erreur, my_data) = rdr.read(B2S8)
        if True: # not Est_Erreur:
            # print("B2S8 avant : ", str(my_data))
            my_data = write_data(subscription_end_date)
            # print("MY DATA : ", str(my_data))
            Est_Erreur = rdr.write(B2S8, my_data)
            if not Est_Erreur:
                pass
                # print("   OK - B2S8") #  : ", str(rdr.read(B2S8)))
            else:
                print("Erreur Ecriture B2S8")       
        # Ecrire clef CC dans le Trailer
        if not Est_Erreur:
            # (Est_Erreur, my_data) = rdr.read(B2S11)
            if True: #  not Est_Erreur:
                my_data = Sector_Key_CC
                Est_Erreur = rdr.write(B2S11, my_data)
                if not Est_Erreur:
                    pass
                    # print("   OK - B2S11")
                else:
                    print("   Erreur Ecriture B2S11") 
    # Conclure
    rdr.stop_crypto()
    return Est_Erreur
#-------------------------------------------------

#-------------------------------------------------------
def Read_SubScription_End_Date_from_Card(current_UID):
# Lit la Date de Fin d'abonnement dans le secteur B2S8
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    my_LVD = "" # la date de fin d'abonnement
    # Try with CC key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST PB")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST PB 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD PB ...")
            # print("UID PB ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT PB ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B2S8, key_CityClub, my_UID)
                        # print("AUTH A PB ...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A CITYCLUB B2S8 OK")
    # Lire
    if not (E_Carte and E_Auth):
        print("Echec Auth B2S8")
        Est_Erreur = True
    else:
        # Lire Subscription End Date dans B2S8
        (Est_Erreur, my_data) = rdr.read(B2S8)
        if not Est_Erreur:
            my_LVD = read_card(my_data)
    # Conclure
    rdr.stop_crypto()
    return Est_Erreur, my_LVD
#-------------------------------------------------

#-------------------------------------------------------
def Write_Last_Visit_Date_to_Card(last_visit_date, current_UID):
# Ecrit la Date de dernière visite dans le secteur B3S12
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    # first try with Public key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST PB")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST PB 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD PB ...")
            # print("UID PB ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT PB ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B3S12, key_public, my_UID)
                        # print("AUTH A PB ...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A PUBLIC B3S12 OK")
    # second try with Public key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD CC ...")
            # print("UID CC ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT CC ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B3S12, key_CityClub, my_UID)
                        # print("AUTH A CC ...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A CITYCLUB B3S12 OK")
    # third try with YAPO key
    if (E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD YP ...")
            # print("UID YP ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                else:
                    # print("SELECT YP ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B3S12, key_YAPO, my_UID)
                        # print("AUTH A YP ...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A YAPO B3S12 OK")
    # Ecrire les blocs et le trailer
    if not (E_Carte and E_Auth):
        print("Echec Auth B3S12")
        Est_Erreur = True
    else:
        # Ecrire Subscription End Date dans B3S12
        # (Est_Erreur, my_data) = rdr.read(B3S12)
        if True: #  not Est_Erreur:
            # print("B3S12 avant : ", str(my_data))
            my_data = write_data(String_replace(last_visit_date))
            # print("MY DATA : ", str(my_data))
            Est_Erreur = rdr.write(B3S12, my_data)
            if not Est_Erreur:
                pass
                # print("   OK - B3S12") #  : ", str(rdr.read(B3S12)))
            else:
                print("Erreur Ecriture B3S12")       
        # Ecrire clef CC dans le Trailer
        if not Est_Erreur:
            # (Est_Erreur, my_data) = rdr.read(B3S15)
            if True: #  not Est_Erreur:
                my_data = Sector_Key_CC
                Est_Erreur = rdr.write(B3S15, my_data)
                if not Est_Erreur:
                    pass
                    # print("   OK - B3S15")
                else:
                    print("   Erreur Ecriture B3S15") 
    # Conclure
    rdr.stop_crypto()
    return Est_Erreur
#-------------------------------------------------


#-------------------------------------------------------
def Read_Last_Visit_Date_from_Card(current_UID):
# Ecrit la Date de dernière visite dans le secteur B3S12
    E_Carte = False
    E_Auth = False
    my_UID = []
    my_data = []
    Est_Erreur = False
    my_LVD = ""
    # first try with Public key
    if True: # (not E_Carte) and (not E_Auth):
        # print("REQUEST PB")
        (error_q, data) = rdr.request()
        if error_q:
            # print("REQUEST PB 2")
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD PB ...")
            # print("UID PB ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                if my_UID != current_UID:
                    E_Carte = False
                    # print("UID différent ...")
                else:
                    # print("SELECT PB ...")
                    error_s = rdr.select_tag(my_UID)
                    if not error_s:
                        error_a = rdr.card_auth(rdr.auth_a, B3S12, key_CityClub, my_UID)
                        # print("AUTH A PB ...") 
                        if not error_a:
                            E_Auth = True
                            print("AUTH A CITYCLUB B3S12 OK")
    # Lire
    if not (E_Carte and E_Auth):
        print("Echec Auth B3S12")
        Est_Erreur = True
    else:
        # Lire Subscription End Date dans B3S12
        (Est_Erreur, my_data) = rdr.read(B3S12)
        if not Est_Erreur:
            my_LVD = from_card(read_card(my_data))
    # Conclure
    rdr.stop_crypto()
    return Est_Erreur, my_LVD
#-------------------------------------------------


#********************************************************
def Detect_Card():
# si une carte est détectée, essaye plusieurs authentification pour renvoyer l'UID, et le Secteur B3S12
    E_Carte = False
    E_Auth = False
    my_UID = []
    B3S12_data = []
    global last_UID
    global last_UID_datetime
    # first try with CC key
    if True: # (not E_Carte) and (not E_Auth):
        (error_q, data) = rdr.request()
        if error_q:
            (error_q, data) = rdr.request()
        if not error_q:
            # print("\nCARD CC ...")
            # print("UID CC ...")
            E_Carte = True
            (error_u, my_UID) = rdr.anticoll()
            if not error_u:
                # print("SELECT CC ...")
                error_s = rdr.select_tag(my_UID)                
                if not error_s:
                    if (my_UID == last_UID) and ((datetime.datetime.utcnow() - last_UID_datetime).total_seconds() <= 10 ): # moins de 10 secondes avec le même UID
                        E_Carte = False
                        # next_action = "" # boucler sans faire d'autres traitements
                        last_UID_datetime = datetime.datetime.utcnow() # mémoriser de nouveau la date/heure du passage
                        print("\nUID déjà lu dans les 10 secondes : ", my_UID)
                        msg("DEJA LU < 10s !", last_message_l2) # réafficher le dernier message de l'écran
                        Wait_for_Card_Removing(tag_uid)
                    else: # initialiser last_UID et last_UID_lasttime
                        last_UID = my_UID
                        last_UID_datetime = datetime.datetime.utcnow()
                        # next_action = "UID" # Traitement de l'UID
                        error_a = rdr.card_auth(rdr.auth_a, B3S12, key_CityClub, my_UID)
                        # print("AUTH A CC ...") 
                        if not error_a:
                            (error_r, B3S12_data) = rdr.read(B3S12)
                            # print("READ CC ...")
                            if not error_r:
                                print("\nReading block B3S12 with CityClub key : " + str(B3S12_data))
                                E_Auth = True
                                rdr.stop_crypto()
##    # second try with Public key
##    if (E_Carte) and (not E_Auth):
##        (error_q, data) = rdr.request()
##        if not error_q:
##            # print("\nCARD PB ...")
##            E_Carte = True
##            # print("UID PB ...")
##            (error_u, my_UID) = rdr.anticoll()
##            if not error_u:
##                error_s = rdr.select_tag(my_UID)
##                if not error_s:
##                    error_a = rdr.card_auth(rdr.auth_a, B3S12, key_public, my_UID)
##                    if not error_a:
##                        (error_r, B3S12_data) = rdr.read(B3S12)
##                        if not error_r:
##                            print("\nReading block B3S12 with Public key : " + str(B3S12_data))
##                            E_Auth = True
##                            rdr.stop_crypto()
##    # third try with YAPO key
##    if (E_Carte) and (not E_Auth):
##        (error_q, data) = rdr.request()
##        if not error_q:
##            E_Carte = True
##            # print("UID YAPO ...")
##            (error_u, my_UID) = rdr.anticoll()
##            if not error_u:
##                error_s = rdr.select_tag(my_UID)
##                if not error_s:
##                    error_a = rdr.card_auth(rdr.auth_a, B3S12, key_YAPO, my_UID)
##                    if not error_a:
##                        (error_r, B3S12_data) = rdr.read(B3S12)
##                        if not error_r:
##                            print("\nReading block B3S12 with YAPO key : " + str(B3S12_data))
##                            E_Auth = True
##                            rdr.stop_crypto()
    # Renvoyer Réponse
    if my_UID == []: # au cas où la carte n'a pas été correctement détectée
        E_Carte = False
        # print(".", end="")
    # else:
        # print("")
    return (E_Carte, E_Auth, my_UID, B3S12_data)
#********************************************************

#********************************************************
def Wait_for_Card_Removing(old_UID):
# Attend jusqu'à ce que la carte soit retirée
    continue_waiting = True
    # rdr.stop_crypto()
    data = []
    while continue_waiting:
        (error_q, data) = rdr.request()
        if error_q:
            (error_q, data) = rdr.request()
        # print("Request : ", error_q)
        if not error_q:
            (error_u, my_UID) = rdr.anticoll()
            # print("UID: ", error_u, old_UID, my_UID)
            if not error_u:
                continue_waiting = (old_UID == my_UID)
            else:
                continue_waiting = False
        else:
            continue_waiting = False
        if continue_waiting:
            print("+", end="")
            time.sleep(0.5)
    # en sortie
    print("")
    time.sleep(1) # afin de laisser le message affiché à l'écran
#********************************************************

#********************************************************
def end_read(signal,frame):
    global continue_reading
    print ("\nLecture terminée")
    msg("MACHINE ARRETEE", "ESSAYEZ + TARD")
    continue_reading = False
    rdr.cleanup()
    GPIO.cleanup()
#********************************************************
    
## Programme principal ##

# Récupération des Paramètres depuis MySQL

# Nom du Raspberry
rbnom=get_param("idreader")
print("Reader name: ",rbnom)

# URL du ping CityClub
url_ping_CC=get_param("Url_ping")
# url_ping_CC=get_param("Url_ping_public")
print("Ping CC sur : ",url_ping_CC)

# URL du WebService CityClub
url_WS=get_param("Url")
# url_WS=get_param("Url_public")
print("WS CC sur : ",url_WS)

# Timeout du WebService CityClub
url_WS_tm=float(get_param("timeout"))
print ("WS Timeout : ",url_WS_tm)

# URL du Ping YAPO
url_yapo_ping="http://update.yapo.ovh/ping/"+societe+"/RPI/"+rbnom
print("Ping YAPO sur:",url_yapo_ping)

# Initialiser le LCD
I2C_ADDR = int(get_param("lcd_addr"))
print("Adresse LCD (I2C_ADDR) : ", end="")
print('0x' + hex(I2C_ADDR)[2:].rjust(2, '0'))
bus = smbus.SMBus(1)
lcd_init()
lcd_byte(0x01,LCD_CMD)
lcd_init()                   

# On bouclera tant que continue_reading = True
continue_reading = True

# Capture SIGINT for cleanup when the script is aborted
signal.signal(signal.SIGINT, end_read)

# Déclaration du module RFID, création d'un objet de la classe MFRC522
# MIFAREReader = MFRC522.MFRC522()

# Déclaration de la 2ème librairie RFID
rdr = RFID()
# util = rdr.util()
# util.debug = True
rdr.cleanup()

# c'est parti
print("Début :")

if True:
    # Boucle principale
    while continue_reading:

        # Afficher un point à chaque passage
        print(".", end="")

        # Mémoriser la Date et l'heure en cours
        strtoday= datetime.datetime.today() # qui sera affiché sur l'écran

        # Display Message LCD L1 et L2
        lcd_string(strtoday.strftime("%Y-%m-%d %H:%M"),LCD_LINE_1)
        lcd_string("Attente Carte",LCD_LINE_2)       
        next_action = "NEW_DETECT"   

        # Détection de la Carte : si une carte est présentée, retourne l'UID et 
        if next_action == "NEW_DETECT":
            (Est_Carte, Est_Auth, tag_uid, data_bloc) = Detect_Card()
            if Est_Carte and len(tag_uid) >= 4:
                Card_Insert = 1
                GCP_UID = '%02X' % tag_uid[0] + '%02X' % tag_uid[1] + '%02X' % tag_uid[2] + '%02X' % tag_uid[3]
                print ("UID de la carte : ",GCP_UID)
                if not Est_Auth: #(data_bloc == None) or (data_bloc[0] != 50) or (data_bloc[1] != 48): # 20xx-xx-xx ...
                    last_visit = ""
                else:
                    back_Data = read_card(data_bloc)
                    last_visit= from_card(back_Data)
                print("Date dernier passage depuis la Carte: [" + last_visit + "]")
                next_action ="WS" # faire appel au WS avec lastvisit initialisé
            else:
                Card_Insert = 0
                last_visit = ""          

        if next_action == "WS":# Appel Web service
            # print("WS")
            # if Card_Init_Status == "YES_INIT":
            # print(GCP_UID,"VEUILLEZ PATIENTER")
            msg(GCP_UID,"PATIENTEZ ...")
            # print("Appel Au web service",last_visit)
            # GCP_UID = "FEAF72F2" # pour les tests
            # GCP_UID = "DD53DE70" # pour les tests
            DATA ='{"idreader":"' + rbnom + '","uid":"' + GCP_UID + '","mode":"online","rpitime":"' + get_rpi_time() + '","lastvisit":"' + last_visit + '"}'
            print("WS : Sent Data : ",DATA)
            response,mode=Appel_Web_Service(DATA) # on récupère en response le json data
            # on récupère dans mode : pas200, online ou exception
            # mode = "pas200" # pour les tests
            if mode == "online":
                print("ON LINE, Réponse du WS:", response.text)
                python_obj=json.loads(response.text)
                mode = python_obj['mode'] ## toujours "online" 
                firstname = python_obj['firstname']
                lastname = python_obj['lastname']
                result= python_obj['result'] # OK ou STOP
                enddate = python_obj['enddate']
                newvisit = python_obj['newvisit']
                # print("DATE DERNIER PASSAGE depuis web service: ", newvisit )
                Date_last_visite = String_replace(newvisit)
                # print("DATE DERNIER PASSAGE VERS CARTE",Date_last_visite )
                next_action = "TT_ONLINE" # mettre à jour la carte et ouvrir passage
                # déjà défini dans l'appel à Appel_Web_Service : Can_Try_Offline_Upload = True # si Vrai, tenter de remonter des infos OFF_LINE
            elif mode == "pas200":
                print("Status Error, Code Réponse du WS:", response.status_code)
                next_action = "TT_OFFLINE"
                # déjà défini dans l'appel à Appel_Web_Service : Can_Try_Offline_Upload = False # si Faux, ne pas tenter de remonter des infos OFF_LINE
                # si carte initialisée, récupérer les info, insérer dans la base et autoriser ou pas le passage
                # si carte pas initialisée, accueil
            elif mode == "exception":
                print("Exception sur le WebService, timeout ?")
                next_action = "TT_OFFLINE"
                # déjà défini dans l'appel à Appel_Web_Service : Can_Try_Offline_Upload = False # si Faux, ne pas tenter de remonter des infos OFF_LINE
                # voir avant
            else:
                print("WebService retourne mode inconnu : ", mode)
                next_action = "TT_OFFLINE"
                Can_Try_Offline_Upload = False # si Faux, ne pas tenter de remonter des infos OFF_LINE
                
        # Traitement ON LINE
        if next_action == "TT_ONLINE":
            print("Traitement ON LINE :") 
            # result = "OK" # pour les tests
            # Autoriser ou pas le passage en fonction de result, initialiser ou mettre à jour la carte
            # Traitement de la carte
            result ="OK" #ici resultat
            if result == "OK":
                Kein_Erreur = False 
                if last_visit == "": # indique que la carte n'était pas initialisée
                    Kein_Erreur = Write_lastname_firstname_to_Card(lastname, firstname, tag_uid)
                    print("Write to Card Lastname / Firstname [" + lastname + "] [" + firstname + "] :" , "OK" if not Kein_Erreur else "Erreur")
                    if not Kein_Erreur:
                        Kein_Erreur = Write_SubScription_End_Date_to_Card(enddate, tag_uid)
                        print("Write to Card Subscription End Date [" + enddate + "] :", "OK" if not Kein_Erreur else "Erreur")
                        if not Kein_Erreur:
                            Kein_Erreur = Write_Last_Visit_Date_to_Card(newvisit, tag_uid)
                            print("Write to Card Last Visit Date [" + newvisit + "] :", "OK" if not Kein_Erreur else "Erreur")
                else: # si la carte était initialisée avec un last_visit != ""
                    Kein_Erreur = Write_Last_Visit_Date_to_Card(newvisit, tag_uid)
                    print("Write to Card Last Visit Date [" + newvisit + "] :", "OK" if not Kein_Erreur else "Erreur")
            # Déclencher le relais / LED
            Traitement_OK_STOP(result)
            msg(firstname+" "+lastname,result+ "   "+enddate)
            next_action = "" # dernier traitement avant de boucler
            
        # Traitement OFF LINE
        if next_action == "TT_OFFLINE":
            print("Traitement OFF LINE : ")
            next_action = "" # dernier traitement avant de boucler
            mode = "offline" # utilisé pour insérer dans la base
            if last_visit == "": # indique que la carte n'était pas initialisée
                Traitement_OK_STOP("BAD") # si pas "OK", va allumer la LED rouge
                msg("OFFLINE", "VOIR ACCUEIL")
            else: # Carte initialisée
                resultat="STOP X02" ; lastname = "" ; firstname = "" ; enddate = "" ; lastvisit = ""
                # Lire le Nom et le Prénom
                Kein_Erreur, lastname, firstname = Read_lastname_firstname_from_Card(tag_uid)
                print("Read from Card Lastname / Firstname : [" + lastname + "] [" + firstname + "] :" , "OK" if not Kein_Erreur else "Erreur")
                if not Kein_Erreur:
                    Kein_Erreur, enddate = Read_SubScription_End_Date_from_Card(tag_uid)
                    print("Read from Card Subscription End Date : [" + enddate + "] :", "OK" if not Kein_Erreur else "Erreur")
                    if not Kein_Erreur:
                        Kein_Erreur, lastvisit = Read_Last_Visit_Date_from_Card(tag_uid)
                        print("Read from Card Last Visit Date : [" + lastvisit + "] :", "OK" if not Kein_Erreur else "Erreur")
                        if not Kein_Erreur:
                            resultat = Date_Comparison(enddate) # OK ou STOP en fonction de l'expiration de la carte
                # Insérer le passage dans la base
                if resultat !="STOP X02": # Carte Inconnue, valeur par défaut si on a pas réussi à lire la carte, ou carte arrachée
                    A_R='OUI' ; A_A='NON'
                    insert_passage(rbnom, GCP_UID, lastname, firstname, enddate, get_rpi_time(), lastvisit, A_A, A_R, resultat)
                    Traitement_OK_STOP(resultat)
                    msg(firstname + " " + lastname, resultat + "   " + change_date_format(enddate))
                else:
                    A_R='NON' ; A_A='OUI'
                    insert_passage(rbnom, GCP_UID, lastname, firstname, enddate, get_rpi_time(), lastvisit, A_A, A_R, resultat)
                    Traitement_OK_STOP("BAD") # si pas "OK", va allumer la LED rouge
                    msg("OFFLINE", "VOIR ACCUEIL")                      

        # si une carte a été insérée, boucler jusqu'à ce que la carte soit retirée
        if Card_Insert == 1:
            Card_Insert = 0 # pour ne pas recommencer à la prochaine boucle sans carte
            Wait_for_Card_Removing(tag_uid)

        # Tous les 120 passages, faire un ping
        boucle_compteur = boucle_compteur + 1
        if (boucle_compteur >= 120):
            ### faire un ping vers le serveur local CityClub
            print("\nPing Local CC : ",end="")
            ping_state, ping_datetime = Ping_Local_CityClub() # ajuste Can_Try_Offline_Upload à True si Ping CC réussi, sinon False
            ### faire un ping vers le serveur YAPO
            print("Ping YAPO : ",end="")
            Ping_Yapo()
            # Réinitialiser le Compteur
            boucle_compteur = 0

        # Remonter les passages off_line
        if Can_Try_Offline_Upload == True:
            traitement_post_online()

        # Attente entre 2 boucles principales
        time.sleep(0.2)

##except Exception as e:
##    print("Arrêt forcé : ", end="")
##    print(e)
    


