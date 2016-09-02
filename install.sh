#!/usr/bin/env bash
set -ue

WifiScriptName='wifi-login2.py'
HookScriptName="90_wifi_login.sh"
NmHookDir='/etc/NetworkManager/dispatcher.d'

# Get the real path to the script's directory, resolving links.
if readlink -f dummy >/dev/null 2>/dev/null; then
  script_path=$(readlink -f "${BASH_SOURCE[0]}")
else
  # Some platforms (OS X, old BSD) don't support readlink -f.
  script_path=$(perl -MCwd -le 'print Cwd::abs_path(shift)' "${BASH_SOURCE[0]}")
fi
ScriptDir=$(dirname $script_path)

Usage="Usage: ./$(basename $0) [-f]
This will set up your system so $WifiScriptName automatically runs whenever
you connect to a wireless network. Currently it only works on Linux systems
using NetworkManager.
It does this by adding a script named $HookScriptName to
$NmHookDir/.
That script executes $ScriptDir/$WifiScriptName when you connect to wifi.
Options:
-f: Force it to overwrite $NmHookDir/$HookScriptName if it exists.
    By default it will not overwrite anything.
NOTE: This will require root privileges for a few commands, but only executes
those couple commands as root with sudo. You don't need to run this script
itself as root."

function fail {
  echo "$@" >&2
  exit 1
}

force=
if [[ $# -gt 0 ]]; then
  if [[ $1 == '-f' ]]; then
    force=true
  else
    fail "$Usage"
  fi
fi

platform=$(uname -s)

case "$platform" in
  Linux)
    if [[ -e $NmHookDir/$HookScriptName ]] && ! [[ $force ]]; then
      fail "Error: $NmHookDir/$HookScriptName already exists."
    fi
    # Print a small script to the NetworkManager directory.
    cat <<EOF | sudo tee $NmHookDir/$HookScriptName > /dev/null
#!/usr/bin/env bash
# Run when the interface (\$1) starts with "wl" (as in "wlan0" or "wlp2s0") and status (\$2) is "up".
if [[ \${1:0:2} == wl ]] && [[ \$2 == up ]]; then
  # Wait 1 second before running the script. If you run it immediately, sometimes the connection
  # still isn't set up properly and you'll get network errors.
  python $ScriptDir/$WifiScriptName -w 1
fi
EOF
    sudo chmod 755 $NmHookDir/$HookScriptName
  ;;
  #TODO: Darwin)
  *)
    fail 'Error: Unsupported OS "'$platform'"'
  ;;
esac
