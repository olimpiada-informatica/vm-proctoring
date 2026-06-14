#!/bin/sh

CONFIGFILE="/etc/oisetup/lock_message.conf"

while true; do
	title="$(grep -e '^title=' "$CONFIGFILE" 2>/dev/null | cut -d= -f2)"
	message="$(grep -e '^message=' "$CONFIGFILE" 2>/dev/null | cut -d= -f2)"
	width="$(grep -e '^width=' "$CONFIGFILE" 2>/dev/null | cut -d= -f2)"
	type="$(grep -e '^type=' "$CONFIGFILE" 2>/dev/null | cut -d= -f2)"
	options="$(grep -e '^options=' "$CONFIGFILE" 2>/dev/null | cut -d= -f2)"
	if test -n "$width"; then
		zenity --"${type:-info}" --width "$width" --title "$title" --text "$message" $options
	else
		zenity --"${type:-info}" --title "$title" --text "$message" $options
	fi
done
