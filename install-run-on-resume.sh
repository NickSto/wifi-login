#!/usr/bin/env bash
set -ue

SCRIPT_NAME="run-on-resume.sh"
LINUX_DIR="/etc/pm/sleep.d"
RESUME_SCRIPT_NAME="99_wifi_login.sh"

function fail {
  echo "$@" >&2
  exit 1
}

if [[ $# -gt 0 ]]; then
  fail "USAGE: sudo ./$(basename $0)
This will install $SCRIPT_NAME so that it will actually be executed when
you wake from sleep.
Currently only works on Linux systems that execute scripts in $LINUX_DIR."
fi

# cd to this script's directory
cd $(dirname $0)
script_dir=$(pwd)

if [[ $EUID != 0 ]]; then
  fail "Error: must run as root."
fi

platform=$(uname -s)

case "$platform" in
  Linux)
    resume_script="$LINUX_DIR/$RESUME_SCRIPT_NAME"
    if [[ -e $resume_script ]]; then
      fail "Error: $resume_script already exists."
    fi
    echo "#!/usr/bin/env bash
$script_dir/$SCRIPT_NAME" > "$resume_script"
    chmod +x "$resume_script"
  ;;
  *)
    fail 'Error: Unsupported OS "'$platform'"'
  ;;
esac
