#!/usr/bin/env python
# Run this when connected to NIH wifi to get internet access. It will
# automatically check the internet access first and only act if it's blocked.
# Or, set it to run periodically (or on wake) with the -d argument to check if
# it's connected to NIH wifi and get access if it is.
import os
import re
import sys
import copy
import urllib
import httplib
import urlparse
import datetime

LOG = sys.stderr

SSIDS = ['NIH-Guest-Network', 'NIH-CRC-Patient', 'JHGuestnet' ]
TEST_URL = 'http://nsto.co/misc/access.txt'
EXPECTED = 'You are connected to the real Internet.'

# If no redirect is found in the "Location:" header of the interception
# response, the login will be sent to the domain listed here (using the SSID as
# the key).
LOGIN_DOMAINS = {
  'JHGuestnet':'1.1.1.1',
}

# Identify gateways by some combination of the SSID, login domain, etc.
GATEWAYS = {
  ('JHGuestnet','1.1.1.1'): 'jhguest',
  ('NIH-CRC-Patient',  'b12-wireless-gateway.cit.nih.gov'): 'nih-b12',
  ('NIH-Guest-Network','b12-wireless-gateway.cit.nih.gov'): 'nih-b12',
  ('NIH-CRC-Patient',  'fernwood-wireless-gateway.cit.nih.gov'): 'nih-fern',
  ('NIH-Guest-Network','fernwood-wireless-gateway.cit.nih.gov'): 'nih-fern',
  ('NIH-CRC-Patient',  'wlan-gateway-b45-outside.net.nih.gov:81'): 'nih-b45',
  ('NIH-Guest-Network','wlan-gateway-b45-outside.net.nih.gov:81'): 'nih-b45',
}

# Path to send the login POST to
paths = {
  'jhguest' :'/login.html',
  'nih-b12' :'/login.html',
  'nih-fern':'/login.html',
  'nih-b45' :'/',
}

# data to send in the POST
post_data = {
  'jhguest': 'buttonClicked=4&err_flag=0&err_msg=&info_flag=0&info_msg=&redirect_url=http%3A%2F%2Fnsto.co%2F&email=nmapsy%40gmail.com',
  'nih-b12': 'buttonClicked=4&redirect_url=www.nih.gov&err_flag=0',
  'nih-fern':'buttonClicked=4&redirect_url=www.nih.gov&err_flag=0',
  'nih-b45': 'authkey=uuaxyqpdkkwqhvjs&Login=nih_guest&Password=welcome2NIH',
}

HEADERS_BASE = {
  'Connection'     :'keep-alive',
  'Cache-Control'  :'max-age=0',
  'Accept'         :'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'User-Agent'     :'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.149 Safari/537.36',
  'Content-Type'   :'application/x-www-form-urlencoded',
  'Accept-Encoding':'gzip,deflate,sdch',
  'Accept-Language':'en-US,en;q=0.8',
}

headers = {
  'jhguest' : copy.deepcopy(HEADERS_BASE),
  'nih-b12' : copy.deepcopy(HEADERS_BASE),
  'nih-fern': copy.deepcopy(HEADERS_BASE),
  'nih-b45' : copy.deepcopy(HEADERS_BASE),
}
headers['jhguest']['Origin']  = 'http://1.1.1.1'
headers['jhguest']['Referer'] = 'http://1.1.1.1/login.html?redirect=nsto.co/'
headers['nih-b12']['Origin']  = 'http://b12-wireless-gateway.cit.nih.gov/',
headers['nih-b12']['Referer'] = 'http://b12-wireless-gateway.cit.nih.gov/fs/customwebauth/login.html?switch_url=http://b12-wireless-gateway.cit.nih.gov/login.html&wlan=NIH-CRC-Patient&redirect=www.nih.gov',
headers['nih-b12']['Cookie']  = 'ncbi_sid=50C95150116F7891_0000SID'
headers['nih-fern']['Origin']  = 'http://fernwood-wireless-gateway.cit.nih.gov/'
headers['nih-fern']['Referer'] = 'http://fernwood-wireless-gateway.cit.nih.gov/fs/customwebauth/login.html?switch_url=http://fernwood-wireless-gateway.cit.nih.gov/login.html&wlan=NIH-CRC-Patient&redirect=www.nih.gov'
headers['nih-fern']['Cookie']  = 'ncbi_sid=50C95150116F7891_0000SID'
headers['nih-b45']['Origin']  = 'http://wlan-gateway-b45-outside.net.nih.gov:81'
headers['nih-b45']['Referer'] = 'http://wlan-gateway-b45-outside.net.nih.gov:81/'
headers['nih-b45']['Cookie']  = 'ncbi_sid=50C95150116F7891_0000SID'

def main():

  ssid = get_ssid()
  # if -d argument is used, detect whether the wifi network is a recognized one
  # and only proceed if it is
  for arg in sys.argv:
    if arg == '-d':
      if ssid in SSIDS:
        LOG.write('Recognized ssid: "'+ssid+'". Proceeding.\n')
      else:
        LOG.write('Unrecognized ssid: "'+ssid+'".\n')
        sys.exit()

  # send an http request to determine if we have unintercepted internet access
  (content, response) = make_request(TEST_URL)
  if response.status == 200 and content == EXPECTED:
    LOG.write('You look connected. Response from '+TEST_URL+' is as expected.\n')
    sys.exit(0)
  else:
    LOG.write('Your connection seems intercepted. Response from '+TEST_URL
      +' is not as expected.\n')

  # determine which network we're on from the intercept response
  domain = get_redirect_domain(response, content)
  if domain is None:
    if ssid in LOGIN_DOMAINS:
      domain = LOGIN_DOMAINS[ssid]
    else:
      fail('Error: could not determine login domain for network '+ssid)
  if (ssid, domain) in GATEWAYS:
    gateway = GATEWAYS[(ssid, domain)]
  else:
    fail('Error: unrecognized gateway for "'+str((ssid, domain))+'"')

  # send accept POST
  conex = httplib.HTTPConnection(domain)
  LOG.write("sending login HTTP request\n")
  conex.request(
    'POST',
    paths[gateway],
    post_data[gateway],
    headers[gateway],
  )
  LOG.write("reading response\n")
  try:
    response = conex.getresponse()
    conex.close()
    LOG.write("Login looks successful!\n")
  except Exception:
    LOG.write("Error: Login unsuccessful. Maybe a bad status line?\n")
    conex.close()


def get_ssid():
  for line in os.popen('/sbin/iwconfig wlan0'):
    match = re.search(r'SSID:"([^"]+)"', line)
    if match:
      return match.group(1)


def make_request(url):
  """Make a request to the given URL and return the result.
  Return values are the returned content and the response object."""
  url_parsed = urlparse.urlsplit(url)
  domain = url_parsed[1]
  path = url_parsed[2]
  if not path:
    path = '/'
  query = url_parsed[3]
  if query:
    path += '?'+query

  sys.stderr.write("making request to "+url+" to determine which wifi "
    +"network you're on\n")
  if url.startswith('https://'):
    conex = httplib.HTTPSConnection(domain)
  else:
    conex = httplib.HTTPConnection(domain)

  try:
    conex.request('GET', path)
  except Exception:
    sys.stderr.write("Error: Failed to make connection.\n")
    raise
  try:
    response = conex.getresponse()
    content = response.read()
    conex.close()
  except Exception:
    sys.stderr.write("Error: Failed to retrieve response or close connection.\n")
    raise
  return (content, response)


#TODO: parse content for meta redirects (use longurl.py)
def get_redirect_domain(response, content):
  """Get the domain of the redirect url from either a "Location:" header or a
  meta refresh element (not yet implemented).
  If none is found, return None"""
  domain = None
  location_url = response.getheader('Location')
  if location_url is None:
    return None
  match = re.search(r'^http://([^/]+)/', location_url)
  if match:
    domain = match.group(1).lower()
  else:
    LOG.write("Error: value of 'Location:' header does not match expected "
      "pattern.\n")
  return domain


def fail(message):
  LOG.write(message+"\n")
  sys.exit(1)


if __name__ == '__main__':
  main()