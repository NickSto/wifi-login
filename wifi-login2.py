#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
import os
import sys
import time
import errno
import socket
import logging
import httplib
import urlparse
import argparse
import datetime
import collections
from lib import ipwraplib

#TODO: There may be security concerns arising from the fact that an SSID can be any sequence of
#      32 bytes instead of a normal string. Check handling of ssid's through the script.

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
REQUEST_DIR_DEFAULT = 'http-login'
SILENCE_FILE = '~/.local/share/nbsdata/SILENCE'

ARG_DEFAULTS = {'request_dir':os.path.join(SCRIPT_DIR, REQUEST_DIR_DEFAULT), 'log':sys.stderr,
                'log_level':logging.WARNING, 'test_url':'http://www.gstatic.com/generate_204',
                'expected_status':204, 'expected_body':'', 'wait':0, 'retries':2, 'retry_pause':0.5}
USAGE = "%(prog)s [options]"
DESCRIPTION = """Automatically log in to wifi networks which prevent access until you accept their
terms of service, provide an email address, etc. First, log in normally and capture the HTTP request
your browser generated in the process. Save it to a file and give its path as the first argument to
this script. Or, you can name the text file [SSID].txt and save it in
"""+ARG_DEFAULTS['request_dir']+', and this script will automatically find it.'

def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('request', metavar='http-request.txt', nargs='?',
    help='A text file containing the full HTTP request that grants access.')
  parser.add_argument('-d', '--request-dir',
    help='The directory containing records of the HTTP requests. Default: %(default)s (A directory '
         'named '+REQUEST_DIR_DEFAULT+' under the script\'s directory).')
  parser.add_argument('-S', '--skip-test', action='store_true',
    help='Skip the connection test and assume we need to log in.')
  parser.add_argument('-u', '--test-url',
    help='The URL to try in order to check if the connection is being intercepted. '
         'Default: %(default)s.')
  parser.add_argument('-s', '--expected-status', type=int,
    help='The HTTP status code expected in response to the test url. Default: %(default)s.')
  #TODO: Allow a None body.
  parser.add_argument('-b', '--expected-body',
    help='The body of the expected response to the test url. Default: "%(default)s".')
  parser.add_argument('-w', '--wait', type=float,
    help='The amount of time to wait before execution, in seconds. Default: %(default)s.')
  parser.add_argument('-r', '--retries', type=int,
    help='The number of times to retry an HTTP request if it fails. Default: %(default)s.')
  parser.add_argument('-R', '--retry-pause', type=float,
    help='The number of seconds to wait between HTTP request retries. Default: %(default)s.')
  parser.add_argument('-q', '--quiet', dest='log_level', action='store_const', const=logging.ERROR,
    help='Print messages only on terminal errors.')
  parser.add_argument('-v', '--verbose', dest='log_level', action='store_const', const=logging.INFO,
    help='Print informational messages in addition to warnings and errors.')
  parser.add_argument('-D', '--debug', dest='log_level', action='store_const', const=logging.DEBUG,
    help='Turn debug messages on.')
  parser.add_argument('-l', '--log', type=argparse.FileType('a'),
    help='Print log messages to this file instead of to stderr. Will append to the file.')
  parser.add_argument('-O', '--overwrite-log', action='store_true',
    help='Overwrite the log file instead of appending to it.')

  args = parser.parse_args(argv[1:])

  # Set up the log file.
  if args.overwrite_log:
    args.log.truncate(0)
  logging.basicConfig(stream=args.log, level=args.log_level, format='%(levelname)s: %(message)s')
  tone_down_logger()

  # Print a starting timestamp to the log.
  now_dt = datetime.datetime.now()
  now_time = int(time.mktime(now_dt.timetuple()))
  logging.info('Started at {} ({})'.format(str(now_dt)[:19], now_time))

  # Exit if we're not supposed to be network-silent right now.
  if os.path.exists(os.path.expanduser(SILENCE_FILE)):
    logging.warn('Silence file ({}) exists. Exiting instead of creating network traffic.'
                 .format(SILENCE_FILE))
    return 0

  # Pause before execution, if requested.
  if args.wait:
    logging.debug('Pausing {} seconds as requested by --wait option..'.format(args.wait))
    time.sleep(args.wait)

  # Find the file containing a record of an HTTP request which grants access to this wifi network.
  if args.request:
    request_file = args.request
  else:
    ssid = ipwraplib.get_wifi_info()[1]
    if not ssid:
      fail('It doesn\'t look like you\'re connected to wifi.')
    request_file = find_request_file(args.request_dir, ssid)
    if request_file:
      logging.debug('Located request file "{}".'.format(request_file))
    else:
      logging.warn('Unrecognized SSID "{}". No request record found in directory {}.'
                   .format(ssid, args.request_dir))
      return 0

  # Read the request file.
  with open(request_file) as request:
    headers, method, path, protocol, post_data = parse_request_file(request)

  # Check if our connection is being intercepted by the wifi access point.
  #TODO: Check where the intercepted response is redirecting us, if it is ("Location" header).
  if not args.skip_test:
    expected = {'status':args.expected_status, 'body':args.expected_body}
    tries_left = args.retries + 1
    while tries_left > 0:
      try:
        clear = is_connection_clear(args.test_url, expected)
        tries_left = 0
      except (socket.error, httplib.HTTPException) as e:
        logging.warn('Test connection failure. Raised a {}: {}'.format(type(e).__name__, e))
        tries_left -= 1
        time.sleep(args.retry_pause)
    if clear:
      logging.info('Looks like you\'re already connected!')
      return 0

  # Make the HTTP request to (hopefully) grant access.
  tries_left = args.retries + 1
  while tries_left > 0:
    try:
      make_request(headers, method, path, protocol, post_data)
      tries_left = 0
    except (socket.error, httplib.HTTPException) as e:
      logging.warn('Request failure. Raised a {}: {}'.format(type(e).__name__, e))
      tries_left -= 1
      time.sleep(args.retry_pause)


def find_request_file(request_dir, ssid):
  expected_filenames = (ssid, ssid+'.txt', ssid.replace(' ', '-')+'.txt')
  logging.debug('Expected request filenames: {}'.format(expected_filenames))
  for filename in os.listdir(request_dir):
    path = os.path.join(request_dir, filename)
    if not os.path.isfile(path):
      continue
    for expected_filename in expected_filenames:
      if filename == expected_filename:
        return path
  return None


def parse_request_file(request_file):
  headers = collections.OrderedDict()
  post_data = ''
  section = 'first'
  for line_raw in request_file:
    line = line_raw.rstrip('\r\n')
    if section == 'first':
      fields = line.split()
      if not len(fields) == 3 or fields[0] not in ('GET', 'POST'):
        logging.error('First line of request file invalid (should look like "GET /path HTTP/1.1"):'
                      '\n\t'+line)
        raise ValueError
      method, path, protocol = fields
      section = 'headers'
    elif section == 'headers':
      c_index = line.find(':')
      if c_index > 0:
        key = normalize_header_name(line[:c_index])
        value = line[c_index+1:].lstrip(' ')
        headers[key] = value
      elif c_index == -1:
        # This should be an empty line after the headers.
        assert not line, line
        section = 'data'
      else:
        raise AssertionError('Invalid colon location in header: '+line)
    elif section == 'data':
      post_data = line
      section = 'done'
    elif section == 'done':
      # We should be done at this point.
      assert not line, ('Non-blank lines found after the first POST data line. All '
                                       'POST data must be on one line.')
  return headers, method, path, protocol, post_data


def make_request(headers, method, path, protocol, post_data):
  # Get the host and port from the headers.
  host_value = headers.get('Host')
  assert host_value, '"Host:" header not found.'
  try:
    host, port = host_value.split(':')
    port = int(port)
  except ValueError:
    host = host_value
    port = 80
  # Edit the headers to remove some of the things which will be auto-filled by httplib.
  del(headers['Host'])
  if 'Content-Length' in headers:
    del(headers['Content-Length'])
  #TODO: Maybe make a general http_request() function both this and is_connection_clear() can use.
  #TODO: Encase in try/except.
  logging.debug('Making connection to {}:{}..'.format(host, port))
  connection = httplib.HTTPConnection(host, port)
  logging.debug('Making request..')
  # Have encountered a socket.gaierror here.
  connection.request(method, path, post_data, headers)
  logging.debug('Getting response..')
  try:
    connection.getresponse()
  except Exception as e:
    logging.warn('Login unsuccessful. Raised a '+type(e).__name__+' exception.')
    raise
  finally:
    logging.debug('Closing connection..')
    connection.close()


def normalize_header_name(name):
  """Standardize capitalization of header field names.
  Capitalizes the first character of every part of the string delimited by dashes:
  "host" -> "Host", "Content-length" -> "Content-Length", etc."""
  parts = name.lower().split('-')
  normalized_parts = [part.capitalize() for part in parts]
  return '-'.join(normalized_parts)


def is_connection_clear(url, expected, timeout=2):
  """Check whether the internet connection is being intercepted by an access point.
  This will make an HTTP request to the given URL and compare the result to the expected one.
  "expected" is a dict with at least two keys: "status" and "body".
  expected['status'] is the expected HTTP response code, as an int.
  expected['body'] is the actual expected response. If it's None, the body won't be checked."""
  # Parse url.
  scheme, host, path, query, fragment = urlparse.urlsplit(url)
  path = path or '/'
  if query:
    path += '?'+query
  # Make connection.
  if scheme == 'http':
    connection = httplib.HTTPConnection(host, timeout=timeout)
  elif scheme == 'https':
    connection = httplib.HTTPSConnection(host, timeout=timeout)
  else:
    raise AssertionError('URL scheme unrecognized: '+url)
  try:
    connection.connect()
    connection.request('GET', path)
    response = connection.getresponse()
  except socket.error as se:
    if se.errno == errno.ENETUNREACH:
      logging.warn('Failed making HTTP connection to test if your connection is blocked. '
                   'You may not be connected to wifi.')
    else:
      logging.warn('Failed making HTTP connection to test if your connection is blocked. '
                   'Raised a '+type(se).__name__+' exception.')
    raise
  except Exception as e:
    logging.warn('Failed making HTTP connection to test if your connection is blocked. '
                 'Raised a '+type(e).__name__+' exception.')
    raise
  connection.close()
  # Is the response as expected?
  # If only an expected status is given (body is None), only that has to match.
  # If a status and body is given, both have to match. This is a little verbose for clarity.
  is_expected = False
  logging.debug('Test URL HTTP response status: {} (expected: {}).'
                .format(response.status, expected['status']))
  if response.status == expected['status']:
    if expected['body'] is None:
      is_expected = True
    else:
      response_body = response.read(len(expected['body']))
      logging.debug('Test URL response body:\n{}\nexpected:\n{}'
                    .format(response_body[:100], expected['body'][:100]))
      if response_body == expected['body']:
        is_expected = True
  return is_expected


def tone_down_logger():
  """Change the logging level names from all-caps to capitalized lowercase.
  E.g. "WARNING" -> "Warning" (turn down the volume a bit in your log files)"""
  for level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
    level_name = logging.getLevelName(level)
    logging.addLevelName(level, level_name.capitalize())


def fail(message):
  logging.error(message)
  sys.exit(1)

if __name__ == '__main__':
  sys.exit(main(sys.argv))
