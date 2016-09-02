wifi-login
==========

First connect to the right wifi network, then run `./wifi-login2.py` to automatically log in.

The script will only fire off the "accept" HTTP request if your internet access is being intercepted (e.g. by an "accept these terms" page) and you're on a recognized wifi network.

To add a wifi network, connect and perform the action necessary to log in while capturing the HTTP request. Put a text file containing the request into `http-login/`, with the name `[SSID].txt`, replacing `[SSID]` with the SSID of the network.

On a Linux OS using NetworkManager, run `sudo ./install.sh` to add an entry to `/etc/NetworkManager/dispatcher.d/` so that it will try to log you in automatically when your wifi connects.
