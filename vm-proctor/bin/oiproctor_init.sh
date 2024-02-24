#!/bin/bash

function randomstring {
	length="${1:-8}"
	openssl rand -base64 "$length" | sed "s/=*$//"
}

sed 's/nameserver 127.0.0.11$/nameserver 127.0.0.1/' /etc/resolv.conf | sponge /etc/resolv.conf

filepath="/opt/oiproctor/etc/tunnel.pwd"
if ! test -f "$filepath"; then
	randomstring 44 > "$filepath"
	echo "================================================================"
	echo "Set PROCTOR_TUNNEL_PASSWORD in vm's /etc/oisetup/profiles/:"
	cat "$filepath"
	echo "================================================================"
fi

filepath="/opt/oiproctor/etc/vmkey.pwd"
if ! test -f "$filepath"; then
	ssh-keygen -t rsa -f "$filepath" -b 2048 -q -N ""
	chown proctor:proctor "$filepath"
	echo "================================================================"
	echo "Paste this content into /home/oi/.ssh/authorized_keys in the vm:"
	cat "$filepath".pub
	echo "================================================================"
fi

filepath="/opt/oiproctor/etc/proctor.pwd"
if ! test -f "$filepath"; then
	randomstring 20 > "$filepath"
	echo "================================================================"
	echo "User proctor's password:"
	cat "$filepath"
	echo "================================================================"
fi
echo "proctor:$(cat "$filepath")" | chpasswd
