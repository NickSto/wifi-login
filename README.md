wifi-login
==========

First connect to the right wifi network, then run `./wifi-login.py` to automatically log in.

The script will only fire off the "accept" HTTP request if your internet access is being intercepted (e.g. by an "accept these terms" page) and you're on a recognized wifi network.

On a Linux OS, run `sudo ./install-run-on-resume.sh` to add an entry to /etc/pm/sleep.d/ so that it will try to log you in automatically when your laptop wakes from sleep.
