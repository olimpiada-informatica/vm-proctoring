#!/bin/bash

test "$1" = "-c" -o "$1" = "--copy" && copy="true"

dir="$(dirname "$0")"
for path in $(find "$dir" -type f); do
        pathdir="$(dirname "$path")"
	test "$pathdir" = "$dir" && continue # Skip files in the root
	echo "$path" | grep -q '/.git' && continue # Skip GIT files
	src="$(realpath "$path")"
	dst="$(echo $path | cut -c "$(echo "$dir" | wc -c)"-)"
	test -z "$copy" && echo ln -sf "$src" "$dst" 2>/dev/null || echo cp -f "$src" "$dst" 2>/dev/null
	if test $? -ne 0; then
		echo "Failed to install $src -> $dst. Aborting" >&2
		exit 1
	fi
done
