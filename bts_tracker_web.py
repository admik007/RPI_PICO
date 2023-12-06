from machine import Pin, WDT
import utime, time, dht, ubinascii, network, random, socket

# MY HOSTS
my_id = ubinascii.hexlify(machine.unique_id()).decode()

#WatchDog
#wdt=WDT(timeout=8300)


# WIFI
wlan = network.WLAN() #  network.WLAN(network.STA_IF)
ssid = ''
password = '12345678901234567890123456'
ip = ''


# INTERNET
APN = "internet"
MCC = ""
MNC = ""
BSIC = ""
CELLID = ""
LAC = ""


# BUTTON CHECK
pwr_key = machine.Pin(14, machine.Pin.OUT)					#GP14 / 19


# UART SETTINGS
uart = machine.UART(0, 115200)


# DESTINATION
host_temp = "http://gps.ztk-comp.sk/"
count = 0


# CPU TEMPERATURE
sensor_temp = machine.ADC(4)
conversion_factor = 3.3 / (65535)
reading = sensor_temp.read_u16() * conversion_factor 
cputemp = str(round(27 - (reading - 0.706)/0.001721,2))


# LED indicator on Raspberry Pi Pico
led = machine.Pin("LED", machine.Pin.OUT)					#GP25/LED
led.value(0)


# FUNCTIONS
def wlan_online():
 wlan = network.WLAN() #  network.WLAN(network.STA_IF)
 wlan.active(True)
 networks = wlan.scan()
 time.sleep(1)
 networks.sort(key=lambda x:x[3],reverse=True)
 for w in networks:
  if ((w[0].decode() == 'private_network') or (w[0].decode() == 'iPhoneXr') or (w[0].decode() == 'private_network_mobile')):
#  if (w[0].decode() == 'iPhoneXr'):
   ssid = w[0].decode()
   wlan = network.WLAN(network.STA_IF)
   wlan.connect(ssid, password)

 # Wait for connect or fail
 max_wait = 5
 while max_wait > 0:
  if wlan.status() < 0 or wlan.status() >= 3:
    break
  max_wait -= 1
  print('waiting for connection... '+str(max_wait))
  led.value(1)
  time.sleep(.5)
  led.value(0)
  time.sleep(.5)


# FUNCTION BLINK
def blink():
 led.value(1)
 time.sleep(.2)
 led.value(0)
 time.sleep(.8)


def quick_blink():
 led.value(1)
 time.sleep(.2)
 led.value(0)
 time.sleep(.2)
 led.value(1)
 time.sleep(.2)
 led.value(0)


# FUNCTION HTTP GET REQUEST
def http_get(url):
 import socket
 _, _, host, path = url.split('/', 3)
 addr = socket.getaddrinfo(host, 80)[0][-1]
 s = socket.socket()
 s.connect(addr)
 s.send(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\n\r\n' % (path, host), 'utf8'))
 while True:
  print('Sending data')
  data = s.recv(4096)
  if data:
   print(str(data, 'utf8'), end='')
  else:
   break
  print('Closing connection')
 s.close()


# Wait response info
def wait_resp_info(timeout=1000):
 prvmills = utime.ticks_ms()
 info = b""
 while (utime.ticks_ms()-prvmills) < timeout:
  if uart.any():
   info = b"".join([info, uart.read(1)])
# print(info.decode())
 return info


# Send AT command
def send_at(cmd, back, timeout=1000):
 blink()
 rec_buff = b''
 uart.write((cmd+'\r\n').encode())
 prvmills = utime.ticks_ms()
 while (utime.ticks_ms()-prvmills) < timeout:
  if uart.any():
   rec_buff = b"".join([rec_buff, uart.read(1)])
 if rec_buff != '':
  if back not in rec_buff.decode():
   print(cmd + ' back:\t' + rec_buff.decode())
   return 0
  else:
   print(rec_buff.decode())
   return 1
 else:
  print(cmd + ' no responce')


# Send AT command and return response information
def send_at_wait_resp(cmd, back, timeout=2000):
 rec_buff = b''
 uart.write((cmd + '\r\n').encode())
 prvmills = utime.ticks_ms()
 while (utime.ticks_ms() - prvmills) < timeout:
  if uart.any():
   rec_buff = b"".join([rec_buff, uart.read(1)])
 if rec_buff != '':
  if back not in rec_buff.decode():
   print(cmd + ' back:\t' + rec_buff.decode())
  else:
   print(rec_buff.decode())
 else:
  print(cmd + ' no responce')
  print("Response information is: ", rec_buff)
 return rec_buff


if send_at("AT+CGREG?", "0,1") == 0:
 print('SIM868 is offline\r\n')
 pwr_key.value(1)
 utime.sleep(1)
 pwr_key.value(0)
 utime.sleep(2)


# START MAIN PROGRAM
waittime = 1
print('Waittime: '+str(waittime))

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
s.bind(addr)
s.listen(1)



while True:
 try:
  led.value(0)
  blink()
  
  ### READING DATA FROM SENSORS #####
  reading = sensor_temp.read_u16() * conversion_factor 
  cputemp = str(round(27 - (reading - 0.706)/0.001721,2))

  send_at("AT+CENG=4,0", "OK")
  uart.write(bytearray(b'AT+CENG?\r\n'))
  rec_buff = wait_resp_info()
  buff = str(rec_buff)
  parts = buff.split(',')
  print(parts)
  if (parts[0] != "b''"):
   MCC=parts[5]
   MNC=parts[6]
   BSIC=parts[7]
   CELLIDhex=parts[8]
   CELLIDdec = int(CELLIDhex, 16)
   CELLID=str(CELLIDdec)
   LAC=parts[9]



  html = """<!DOCTYPE html>
<html>
 <head>
  <title>"""+my_id+"""</title>
  <meta http-equiv='refresh' content='10'>
 </head>
 <body>
  <b>CPU_Temp:</b> """+cputemp+"""<br>
  <b>MCC:</b> """+MCC+"""<br>
  <b>MNC:</b> """+MNC+"""<br>
  <b>BSIC:</b> """+BSIC+"""<br>
  <b>CELLID:</b> """+CELLID+"""<br>
  <b>LAC:</b> """+LAC+"""<br>
 </body>
</html>
"""

  status = wlan.ifconfig()
  print(str(count)+" of "+str(waittime)+" IP: "+status[0])
  if(status[0] == '0.0.0.0'):
   print('WLAN not connected. Trying connect.')
   wlan_online()
 
  if (count < waittime):
   count+=1
  else:
   waittime = (random.randint(1, 2))
   print('Waittime: '+str(waittime))
   count = 0
   print("-----------------------------")
   print("Device:      "+my_id)
   print("CPU temp:    {}°C ".format(cputemp))
   print("-----------------------------")
   print('MCC '+MCC)
   print('MNC '+MNC)
   print('BSIC '+BSIC)
   print('CELLID '+CELLID)
   print('LAC '+LAC)
   print("=============================")
#   url_temp=str(host_temp+"?devicerpi="+my_id+"&cputemp="+cputemp+"&temp="+temp+"&hum="+hum+"&IP="+status[0])
   if(status[0] != '0.0.0.0'):
    quick_blink()
#    http_get(url_temp)    
   cl, addr = s.accept()
   print('client connected from', addr)
   request = cl.recv(1024)
   request = str(request)
   response = html #% request
   cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
   cl.send(response)
   cl.close()
   
 except OSError as e:
  led.value(1)
  cl.close()
  print('connection closed - OS error')
  
 except KeyboardInterrupt:
  led.value(1)
  cl.close()
  print('connection closed - Interrupted')
