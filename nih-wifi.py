#!/usr/bin/env python
# Run this when connected to NIH wifi to get internet access. It will
# automatically check the internet access first and only act if it's blocked.
# Or, set it to run periodically (or on wake) with the -d argument to check if
# it's connected to NIH wifi and get access if it is.

import datetime
import httplib
import urllib
import sys
import os
import re

DEBUG = False

SSIDS = ['NIH-Guest-Network', 'NIH-CRC-Patient']
TESTSITE = 'www.nih.gov'
GATEWAYS = ['b12', 'fern', 'out']
HEADERS_BASE = {
  'Connection'     :'keep-alive',
  'Cache-Control'  :'max-age=0',
  'Accept'         :'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Origin'         :'http://b12-wireless-gateway.cit.nih.gov/',
  'User-Agent'     :'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36',
  'Content-Type'   :'application/x-www-form-urlencoded',
  'Referer'        :'http://b12-wireless-gateway.cit.nih.gov/fs/customwebauth/login.html?switch_url=http://b12-wireless-gateway.cit.nih.gov/login.html&wlan=NIH-CRC-Patient&redirect=www.nih.gov',
  'Accept-Encoding':'gzip,deflate,sdch',
  'Accept-Language':'en-US,en;q=0.8',
  'Cookie'         :'ncbi_sid=50C95150116F7891_0000SID',
}
PARAMS_BASE = {
  'buttonClicked':'4',
  'redirect_url' :'www.nih.gov',
  'err_flag'     :'0',
}

nicknames = {
  'b12-wireless-gateway.cit.nih.gov'     :'b12',
  'fernwood-wireless-gateway.cit.nih.gov':'fern',
  'wlan-gateway-b45-outside.net.nih.gov' :'out',
}

ports = {
  'b12' :'',
  'fern':'',
  'out' :':81'
}

paths = {
  'b12' :'/login.html',
  'fern':'/login.html',
  'out' :'/',
}

params = {}
params['b12'] = params['fern'] = PARAMS_BASE
params['out'] = {
  'authkey':'uuaxyqpdkkwqhvjs',
  'Login':'nih_guest',
  'Password':'welcome2NIH',
}

headers = {}
headers['b12'] = headers['fern'] = headers['out'] = HEADERS_BASE
headers['fern']['Origin'] = 'http://fernwood-wireless-gateway.cit.nih.gov/'
headers['fern']['Referer'] = 'http://fernwood-wireless-gateway.cit.nih.gov/fs/customwebauth/login.html?switch_url=http://fernwood-wireless-gateway.cit.nih.gov/login.html&wlan=NIH-CRC-Patient&redirect=www.nih.gov'
headers['out']['Origin'] = 'http://wlan-gateway-b45-outside.net.nih.gov:81'
headers['out']['Referer'] = 'http://wlan-gateway-b45-outside.net.nih.gov:81/'

if DEBUG:
  debug_fh = open('/home/me/tmp/nih-debug.txt', 'a')
else:
  debug_fh = open(os.devnull, 'a')
debug_fh.write(str(datetime.datetime.now())+"\n")

# if -d argument is used, detect whether the wifi network is a recognized one
# and only proceed if it is
detect = False
for arg in sys.argv:
  if arg == '-d':
    detect = True
ssid = '';
line1 = "";
if detect:
  for line in os.popen('/sbin/iwconfig wlan0'):
    if line1 == "":
      line1 = line
    match = re.search(r'SSID:"([^"]+)"', line)
    if match:
      ssid = match.group(1)
      break
  if ssid not in SSIDS:
    debug_fh.write('unrecognized ssid: "'+ssid+'" in line:\n'+line1)
    exit()
debug_fh.write('recognized ssid: "'+ssid+'". Proceeding.\n')
debug_fh.close()

# send an http request to determine which network we're connected to
sys.stderr.write("making request to "+TESTSITE+" to determine which wifi "
  +"network you're on\n")
conex = httplib.HTTPConnection(TESTSITE)
try:
  conex.request('GET', '/')
except Exception:
  sys.stderr.write("Error: Failed to make connection.\n")
  exit()
try:
  response = conex.getresponse()
  conex.close()
except Exception:
  sys.stderr.write("Error: Failed to retrieve response or close connection.\n")
  exit()
location_url = response.getheader('Location')
if location_url is None:
  if response.status == 200:
    # test whether the response header looks like it came from www.nih.gov
    if (response.getheader('Date') is not None and
      str(response.getheader('Transfer-Encoding')) == 'chunked' and
      str(response.getheader('Server')) == 'Sun-Java-System-Web-Server/7.0'):
      print "Looks like you're already connected!"
    else:
      sys.stderr.write("Either you've connected to a novel wifi network "
        +"without the 'Location:' header\nin its response or www.nih.gov has "
        +"changed its response headers.\nThe full response header:\n\n")
      for line in response.getheaders():
        sys.stderr.write(line[0]+': '+line[1]+"\n")
  else:
    sys.stderr.write("Error in the response. HTTP status code: "+
      str(response.status)+"\n")
  exit()
match = re.search(r'^http://([^/]+)/', location_url)
if match:
  domain = match.group(1).lower()
else:
  sys.stderr.write("Error: value of 'Location:' header does not match expected "
    +"pattern.\n")
  exit()
if domain not in nicknames:
  sys.stderr.write("Error: connected to a new, unrecognized network: "+domain)
  exit()
print "determined you are connected to "+domain
gateway = nicknames[domain]


# send accept POST
conex = httplib.HTTPConnection(domain+ports[gateway])
sys.stderr.write("sending login HTTP request\n")
conex.request(
  'POST',
  paths[gateway],
  urllib.urlencode(params[gateway]),
  headers[gateway],
)
sys.stderr.write("reading response\n")
try:
  response = conex.getresponse()
  conex.close()
  print "Login looks successful!"
except Exception:
  sys.stderr.write("Error: Probably a bad status line. Trying a different domain..\n")
  conex.close()