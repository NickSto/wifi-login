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

Usage="Usage: sudo ./$(basename $0)
This will set up your system so $WifiScriptName automatically runs whenever you connect to a
wireless network. Currently it only works on Linux systems using NetworkManager.
It does this by adding a script named $HookScriptName to $NmHookDir/.
That script executes $ScriptDir/$WifiScriptName when you connect to wifi."

function fail {
  echo "$@" >&2
  exit 1
}

if [[ $# -gt 0 ]]; then
  fail "$Usage"
fi

if [[ $EUID != 0 ]]; then
  fail "Error: must run as root."
fi

platform=$(uname -s)

case "$platform" in
  Linux)
    if [[ -e $NmHookDir/$HookScriptName ]]; then
      fail "Error: $NmHookDir/$HookScriptName already exists."
    fi
    # Print a small script to the NetworkManager directory.
    cat <<EOF > $NmHookDir/$HookScriptName
#!/usr/bin/env bash
if [[ \${1:0:2} == wl ]] && [[ \$2 == up ]]; then
  python $ScriptDir/$WifiScriptName -D
fi
EOF
    chmod 755 $NmHookDir/$HookScriptName
  ;;
  *)
    fail 'Error: Unsupported OS "'$platform'"'
  ;;
esac
