#!/bin/bash

# Functions (copied from oisetup)
function error {
        echo -e "$@" >&2
        exit 1
}

# Context checks
test "$EUID" -ne 0 && error "This script must be run as root!"

# Commandline checks
test "$1" = "-c" -o "$1" = "--copy" && copy="true"

# Link/Copy files
dir="$(dirname "$0")"
for path in $(find "$dir" -type f); do
        pathdir="$(dirname "$path")"
	test "$pathdir" = "$dir" && continue # Skip files in the root
	echo "$path" | grep -q '/.git' && continue # Skip GIT files
	src="$(realpath "$path")"
	dst="$(echo $path | cut -c "$(echo "$dir" | wc -c)"-)"
	mkdir -p "$(dirname "$dst")"
	test -z "$copy" && ln -sf "$src" "$dst" 2>/dev/null || cp -f "$src" "$dst" 2>/dev/null
	if test $? -ne 0; then
		echo "Failed to install $src -> $dst. Aborting" >&2
		exit 1
	fi
done

# Reload systemd daemon to load the installed files
systemctl daemon-reload