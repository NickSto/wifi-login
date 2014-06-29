#!/usr/bin/env bash
set -ue

SLEEP=5 # seconds
TOTAL=60 # seconds

if [[ $# -gt 0 ]]; then
  echo "USAGE: ./$(basename $0)
This will run './wifi-login.py -d' every $SLEEP seconds for $TOTAL seconds or until a
connection is made.
This is useful for, say, running on resume, when your wifi requires you to login
again after sleeping. On Linux, you should be able to do this by putting a
script in /etc/pm/sleep.d/ which executes this one." >&2
  exit 1
fi

# cd to the script's directory
cd $(dirname $0)

i=0
while [[ $i -lt $TOTAL ]]; do
  result=$(./wifi-login.py -d 2>/dev/null)
  if [[ $result == "connected" ]]; then
    echo $result
    exit 0
  fi
  sleep $SLEEP
  i=$((i+SLEEP))
done
