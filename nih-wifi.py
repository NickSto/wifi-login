#!/usr/bin/env python

import httplib
import urllib
import sys

GATEWAYS = ['b12', 'fern', 'out']
HEADERS_BASE = {
  'Connection':'keep-alive',
  'Cache-Control':'max-age=0',
  'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Origin':'http://b12-wireless-gateway.cit.nih.gov/',
  'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36',
  'Content-Type':'application/x-www-form-urlencoded',
  'Referer':'http://b12-wireless-gateway.cit.nih.gov/fs/customwebauth/login.html?switch_url=http://b12-wireless-gateway.cit.nih.gov/login.html&wlan=NIH-CRC-Patient&redirect=www.nih.gov',
  'Accept-Encoding':'gzip,deflate,sdch',
  'Accept-Language':'en-US,en;q=0.8',
  'Cookie':'ncbi_sid=50C95150116F7891_0000SID',
}
PARAMS_BASE = {
  'buttonClicked':'4',
  'redirect_url':'www.nih.gov',
  'err_flag':'0',
}

domains = {}
domains['b12'] = 'b12-wireless-gateway.cit.nih.gov'
domains['fern'] = 'fernwood-wireless-gateway.cit.nih.gov'
domains['out'] = 'wlan-gateway-b45-outside.net.nih.gov:81'

headers = {}
headers['b12'] = headers['fern'] = headers['out'] = HEADERS_BASE
headers['fern']['Origin'] = 'http://fernwood-wireless-gateway.cit.nih.gov/'
headers['fern']['Referer'] = 'http://fernwood-wireless-gateway.cit.nih.gov/fs/customwebauth/login.html?switch_url=http://fernwood-wireless-gateway.cit.nih.gov/login.html&wlan=NIH-CRC-Patient&redirect=www.nih.gov'
headers['out']['Origin'] = 'http://wlan-gateway-b45-outside.net.nih.gov:81'
headers['out']['Referer'] = 'http://wlan-gateway-b45-outside.net.nih.gov:81/'

paths = {}
paths['b12'] = paths['fern'] = '/login.html'
paths['out'] = '/'

params = {}
params['b12'] = params['fern'] = PARAMS_BASE
params['out'] = {
  'authkey':'uuaxyqpdkkwqhvjs',
  'Login':'nih_guest',
  'Password':'welcome2NIH',
}

for gateway in GATEWAYS:

  sys.stderr.write("calling httplib.HTTPConnection()\n")
  conex = httplib.HTTPConnection(domains[gateway])
  sys.stderr.write("calling conex.request()\n")
  conex.request(
    'POST',
    paths[gateway],
    urllib.urlencode(params[gateway]),
    headers[gateway]
  )
  sys.stderr.write("calling conex.getresponse()\n")
  try:
    response = conex.getresponse()
    conex.close()
    break
  except Exception, e:
    sys.stderr.write("Error: Probably a bad status line. Trying a different domain..\n")
    conex.close()

# sys.stderr.write("printing response data\n")
# print "response.status:\n"+str(response.status)+"\n"
# print "response.reason:\n"+str(response.reason)+"\n"
# print "response.msg:\n"+str(response.msg)+"\n"
# print "response.read():\n"+str(response.read())+"\n"