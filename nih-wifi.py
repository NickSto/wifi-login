#!/usr/bin/env python
# Note: This is for connecting to 'NIH-CRC-Patient'

import cookielib
import httplib
import urllib
import sys

b12 = 'b12-wireless-gateway.cit.nih.gov'
fernwood = 'fernwood-wireless-gateway.cit.nih.gov'

domain = b12

params = urllib.urlencode(
  {
    'buttonClicked':'4',
    'redirect_url':'www.nih.gov',
    'err_flag':'0',
  }
)

headers = {
  'Connection':'keep-alive',
  'Cache-Control':'max-age=0',
  'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Origin':'http://'+domain+'/',
  'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36',
  'Content-Type':'application/x-www-form-urlencoded',
  'Referer':'http://'+domain+'/fs/customwebauth/login.html?switch_url=http://'+domain+'/login.html&wlan=NIH-CRC-Patient&redirect=www.nih.gov',
  'Accept-Encoding':'gzip,deflate,sdch',
  'Accept-Language':'en-US,en;q=0.8',
  'Cookie':'ncbi_sid=50C95150116F7891_0000SID',
}

sys.stderr.write("calling httplib.HTTPConnection()\n")
conex = httplib.HTTPConnection(domain)
sys.stderr.write("calling conex.request()\n")
conex.request('POST', '/login.html', params, headers)

sys.stderr.write("calling conex.getresponse()\n")
try:
  response = conex.getresponse()
except Exception, e:
  sys.stderr.write("Error: Probably a bad status line. Trying a different domain..\n")
  conex.close()

  domain = fernwood
  headers['Origin'] = 'http://'+domain+'/'
  headers['Referer'] = 'http://'+domain+'/fs/customwebauth/login.html?switch_url=http://'+domain+'/login.html&wlan=NIH-CRC-Patient&redirect=www.nih.gov',
  sys.stderr.write("calling httplib.HTTPConnection()\n")
  conex = httplib.HTTPConnection(domain)
  sys.stderr.write("calling conex.request()\n")
  conex.request('POST', '/login.html', params, headers)
  sys.stderr.write("calling conex.getresponse()\n")
  try:
    response = conex.getresponse()
  except Exception, e:
    sys.stderr.write("Error again. Connection unsuccessful.\n")
    conex.close()

# sys.stderr.write("printing response data\n")
# print "response.status:\n"+str(response.status)+"\n"
# print "response.reason:\n"+str(response.reason)+"\n"
# print "response.msg:\n"+str(response.msg)+"\n"
# print "response.read():\n"+str(response.read())+"\n"

conex.close()