#!/usr/bin/env bash
set -ue

SLEEP=5 # seconds
TOTAL=60 # seconds
SILENCE="$HOME/.local/share/nbsdata/SILENCE"

if [[ $# -gt 0 ]]; then
  if [[ $1 == '-h' ]]; then
    echo "USAGE: ./$(basename $0) [resume]
This will run './wifi-login.py -d' every $SLEEP seconds for $TOTAL seconds or until a
connection is made.
This is useful for, say, running on resume, when your wifi requires you to login
again after sleeping. On Linux, you should be able to do this by putting a
script in /etc/pm/sleep.d/ which executes this one, passing on its first argument." >&2
    exit 1
  elif [[ $1 != 'resume' ]]; then
    # Only run when resuming.
    # Scripts in /etc/pm/sleep.d/ are run on every power event, and receive a
    # first argument which tells them whether the system is suspending,
    # resuming, hibernating, etc. This script should be called by one in
    # /etc/pm/sleep.d/ which passes on its first argument.
    exit 0
  fi
fi

# cd to the script's directory
cd $(dirname $0)

i=0
while [[ $i -lt $TOTAL ]]; do
  if [[ ! -e $SILENCE ]]; then
    result=$(./wifi-login.py -d)
    if [[ $result == "connected" ]]; then
      echo $result
      exit 0
    fi
  fi
  sleep $SLEEP
  i=$((i+SLEEP))
done

