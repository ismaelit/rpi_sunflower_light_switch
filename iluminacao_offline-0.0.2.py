#!/usr/bin/python
# -*- coding: utf-8 -*-

# -----------------------------------------------------------------------------
# Liga e desliga a iluminacao noturna de acordo com sua posicao GPS
# e o horario exato do crepusculo na sua posicao do globo (GPS).
#
# Manter o script em memoria: sudo nohup python iluminacao.py & 
# Eh recomendado iniciar pelo Crontab
#
# Desenvolvido por ISMAEL ITTNER (ismael.it@gmail.com)
# Versao 0.0.3 01/04/2017 19:51 
# -----------------------------------------------------------------------------

# instalando bibliotecas no raspbian
# sudo apt-get install python3-pip
# pip3 install schedule datetime threading 

import RPi.GPIO as GPIO
import json, requests, schedule, os  # pip install schedule
from time import time, sleep
from datetime import datetime, timedelta
from threading import Thread

delay_on      =  1 # quantas horas antes (-) ou depois (+) acender a luz
delay_off	  = -2 # quantas horas antes (-) ou depois (+) apagar a luz
GPIO_buzzer	  = 27 # output para o buzzer que bipa ao toggle
GPIO_luz      =  4 # output 3.3v para ligar o rele da luz
GPIO_luz_botao= 20 # input GND para botao pressionado toggle luz
GPIO_heart	  = 12 # led piscando apenas para identificar programa rodando
latitude      = -26.3044084 # sua localizacao para calcular a tangente do sol 
longitude     = -48.8463831 # sua localizacao para calcular a tangente do sol 
file_json_sun = 'sunrise_sunset.json' # nome do arquivo para salvar json em 
				                      # caso de falta de conexao a internet

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_luz, GPIO.OUT, initial=0) #luz
GPIO.setup(GPIO_buzzer, GPIO.OUT, initial=0) #buzzer
GPIO.setup(GPIO_heart, GPIO.OUT, initial=0) #heartbeet
GPIO.setup(GPIO_luz_botao, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# GPIO.output(4, True)

def heartbeet():
	while True: 
		GPIO.output(GPIO_heart, True)
		sleep(0.05)
		GPIO.output(GPIO_heart, False)
		sleep(0.1)
		GPIO.output(GPIO_heart, True)
		sleep(0.05)
		GPIO.output(GPIO_heart, False)
		sleep(1)

def beep(n):
	count = 0
	while (count < n):
		GPIO.output(GPIO_buzzer, 1)
		sleep(0.05)
		GPIO.output(GPIO_buzzer, 0)
		sleep(0.05)
		count = count + 1

def now_utc():
	return datetime.strptime(datetime.utcnow().strftime('%H:%M:%S'), '%H:%M:%S')

def pprint(t): # pretty print
	print(datetime.now().strftime('%H:%M:%S') + ' ' + t)
	return

def luz(t):
	global luz_state
	luz_state = t 
	if (t==1) or (t==True):
		beep(2)
		GPIO.output(GPIO_luz, t)
		pprint("ligando luz...")
	elif (t==0) or (t==False):
		beep(1)
		GPIO.output(GPIO_luz, t)
		pprint("desligando luz...")
	else: 
		return

luz(0)

global botao_bypass #caso tenha sido forcado acendimento ou desligamento, manter status ate outro dia
botao_bypass = 0 
def botao():
	while True: 
		global botao_bypass
		input_state = GPIO.input(GPIO_luz_botao)
		if input_state == 0:
			if (luz_state == 1):
				pprint('luz desligada manualmente...')
				luz(0)
				if (is_night == 1):
					botao_bypass = 1
				else:
					botao_bypass = 0
			else:
				pprint('luz ligada manualmente...')
				luz(1)
				if (is_night == 1):
					botao_bypass = 0
				else:
					botao_bypass = 2
		sleep(0.25)

th=Thread(target=heartbeet)
th.start()
th=Thread(target=botao)
th.start()

def sun_utc():
	# global sun_data
	pprint('obtendo sunrise/sunset...')
	try :
		url = "http://api.sunrise-sunset.org/json"
		params = dict(lat=latitude,lng=longitude,formatted=0)
		r = requests.get(url=url, params=params)
		sun_data = r.json()
		return sun_data
	except Exception:
		pprint('erro ao tentar obter sunrise/sunset')
		return 0

def sun_file():
	sun_data = sun_utc()
	if (sun_data == 0):
		if (os.path.isfile(file_json_sun) == True):
			f = open(file_json_sun, 'r')
			pprint('usando sunrise/sunset do ultimo request com sucesso...')
			sun_data = eval(f.read()) # eval transforma string para dict
			f.close()
			return sun_data
		elif (os.path.isfile(file_json_sun) == False):
			pprint('tentando obter sunrise/sunset pela primeira vez...')
			n = 0
			while (sun_data == 0):
				n = n + 1
				pprint('tentativa ' + str(n) + '...')
				sun_data = sun_utc()
				sleep(5)
	else: 
		pprint('gravando último JSON sunrise/sunset: ' + file_json_sun)
		f = open(file_json_sun, 'w')
		f.write(str(sun_data)) # str transforma dict para string
		f.close()
		return sun_data

def get_sun():
	# HORA FORMATADA DO JSON SUN EM UTC 
	# results_sunrise = '2017-03-29T09:23:38+00:00'
	# results_sunset  = '2017-03-29T21:16:09+00:00'
	sun_data = sun_file()
	results_sunrise = sun_data['results']['sunrise']
	results_sunset  = sun_data['results']['sunset']
	global sunrise_utc_obj
	sunrise_utc_obj = datetime.strptime(results_sunrise[11:19], '%H:%M:%S') + timedelta(hours=delay_off)
	global sunset_utc_obj
	sunset_utc_obj  = datetime.strptime(results_sunset[11:19],  '%H:%M:%S') + timedelta(hours=delay_on)

schedule.every().day.at("12:00").do(get_sun)

get_sun()

while True: 
	if (now_utc() > sunset_utc_obj) or (now_utc() < sunrise_utc_obj):
		is_night = 1
		if (luz_state == 0) and (botao_bypass == 0):
			luz(1)
	else:
		is_night = 0 
		if (luz_state == 1) and (botao_bypass == 0): 
			luz(0)

	if (is_night == 0) and (botao_bypass == 1):
		botao_bypass = 0
	elif (is_night == 1) and (botao_bypass == 2):
		botao_bypass = 0
	sleep(3)

