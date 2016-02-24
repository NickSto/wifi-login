#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
import sys
import httplib
import argparse
import collections

ARG_DEFAULTS = {}
USAGE = "%(prog)s [options]"
DESCRIPTION = """"""


def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('request', metavar='http-request.txt',
    help='A text file containing the full HTTP request that grants access.')

  args = parser.parse_args(argv[1:])

  with open(args.request) as request:
    headers, method, path, protocol, post_data = parse_request_file(request)

  make_request(headers, method, path, protocol, post_data)


def parse_request_file(request_file):
  headers = collections.OrderedDict()
  post_data = ''
  section = 'first'
  for line in request_file:
    if section == 'first':
      fields = line.rstrip('\r\n').split()
      assert len(fields) == 3, fields
      method, path, protocol = fields
      assert method in ('GET', 'POST'), method
      section = 'headers'
    elif section == 'headers':
      c_index = line.find(':')
      if c_index > 0:
        key = normalize_header_name(line[:c_index])
        value = line[c_index+1:].lstrip(' ').rstrip('\r\n')
        headers[key] = value
      elif c_index == -1:
        # This should be an empty line after the headers.
        assert not line.rstrip('\r\n'), line
        section = 'data'
      else:
        raise AssertionError('Invalid colon location in header: '+line)
    elif section == 'data':
      post_data = line.rstrip('\r\n')
      section = 'done'
    elif section == 'done':
      # We should be done at this point.
      assert not line.rstrip('\r\n'), ('Non-blank lines found after the first POST data line. All '
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
  print('Making connection to {}:{}..'.format(host, port))
  connection = httplib.HTTPConnection(host, port)
  print('Making request..')
  connection.request(method, path, post_data, headers)
  print('Getting response..')
  try:
    connection.getresponse()
  except Exception:
    sys.stderr.write("Error: Login unsuccessful. Maybe a bad status line?\n")
  finally:
    print('Closing connection..')
    connection.close()


def normalize_header_name(name):
  """Standardize capitalization of header field names.
  Capitalizes the first character of every part of the string delimited by dashes:
  "host" -> "Host", "Content-length" -> "Content-Length", etc."""
  parts = name.lower().split('-')
  normalized_parts = [part.capitalize() for part in parts]
  return '-'.join(normalized_parts)


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  sys.exit(main(sys.argv))
