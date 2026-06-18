#!/bin/bash

REPO_NAME="vm-proctoring"
REPO_URL="https://github.com/olimpiada-informatica/$REPO_NAME"
REPO_PATH="/opt/$REPO_NAME"

# Functions
function error {
        echo -e "$@" >&2
        exit 1
}

# Context checks
test "$EUID" -ne 0 && error "This script must run with root privileges!"

# Commandline checks
test "$1" = "-c" -o "$1" = "--copy" && copy="true"
test "$1" = "-s" -o "$1" = "--silent" && silent="true"

# Restore full internet access
dns-lockdown stop 2>/dev/null # The command may not yet be installed

# Download the repo
if test ! -d "$REPO_PATH"; then
        echo "Installing from repo..."
        git clone "$REPO_URL" "$REPO_PATH" || error "Failed to download from the repository."
elif test "$(git -C "$REPO_PATH" ls-remote "$REPO_URL" refs/heads/main | cut -f1)" != "$(git -C "$REPO_PATH" rev-parse refs/heads/main)"; then
        echo "Updating from repo..."
        git -C "$REPO_PATH" pull || error "Failed to download from the repository! Internet access is left fully open."
fi

# Re-enable internet restrictions
dns-lockdown start 2>/dev/null # The command may not yet be installed

# Delete proctor server files
if test -d "$REPO_PATH/vm-proctor"; then
	echo "Deleting proctor server repo files..."
	rm -rf "$REPO_PATH/vm-proctor"
fi

# Link/Copy files
dir="$REPO_PATH/vm-contestant"
for path in $(find "$dir" -type f); do
        pathdir="$(dirname "$path")"
	test "$pathdir" = "$dir" && continue # Skip files in the root
	echo "$path" | grep -q '/.git' && continue # Skip git files
	src="$(realpath "$path")"
	dst="$(echo $path | cut -c "$(echo "$dir" | wc -c)"-)"
	mkdir -p "$(dirname "$dst")"
	test -z "$copy" && ln -sf "$src" "$dst" 2>/dev/null || cp -f "$src" "$dst" 2>/dev/null
	test $? -ne 0 && error "Failed to install $src -> $dst. Aborting"
done
! test -d /etc/oisetup/logos && mkdir /etc/oisetup/logos && chmod a+rx /etc/oisetup/logos

# Reload systemd daemon to load the installed files
systemctl daemon-reload || error "Failed to reload systemd settings"

# Ready
test -z "$silent" && echo "You may now run: oisetup <profile> -i -c" # Only show if not called from `oisetup`

# Return success for oisetup to continue
true