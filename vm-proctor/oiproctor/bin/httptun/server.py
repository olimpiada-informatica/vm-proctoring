#!/usr/bin/env python3
# Based on https://github.com/veluca93/httptun
import datetime
import os
import sys
import threading
import traceback
import urllib.parse
import binascii
import json
from queue import Queue, Empty

from common import get_mac, BROADCAST, dequeue, parse_packets, serialize_packets
from pytun import TunTapDevice, IFF_TAP
from wsgiserver import WSGIServer

MYMAC = b'ter000'
IP_PREFIX = (10, 9)
VARRUNPATH = "/opt/oiproctor/run/connections"
MAC_IP_MAPFILE = "/opt/oiproctor/run/mac_ip_map.json"

ip_sequential = 2

queue = dict()
ips = dict()


def load_mac_ip_map():
    """Load the MAC-to-IP mapping from persistent storage"""
    global ips, ip_sequential
    if os.path.exists(MAC_IP_MAPFILE):
        try:
            with open(MAC_IP_MAPFILE, "r") as f:
                data = json.load(f)
                ips = {binascii.unhexlify(k): bytes(v) for k, v in data.items()}
                # Find the highest ip_sequential used
                for ip in ips.values():
                    ip_int = (ip[2] << 8) + ip[3]
                    if ip_int >= ip_sequential:
                        ip_sequential = ip_int + 1
        except:
            traceback.print_exc()


def save_mac_ip_map():
    """Save the MAC-to-IP mapping to persistent storage"""
    varrundir = os.path.dirname(MAC_IP_MAPFILE)
    if not os.path.exists(varrundir):
        os.makedirs(varrundir)
    try:
        with open(MAC_IP_MAPFILE, "w") as f:
            data = {binascii.hexlify(k).decode('ascii'): list(v) for k, v in ips.items()}
            json.dump(data, f)
    except:
        traceback.print_exc()


def init_queue(dest_mac):
    queue[dest_mac] = Queue()


def put_in_queue(dest_mac, data):
    if dest_mac == BROADCAST:
        for k in queue:
            queue[k].put(data)
        return True
    if not dest_mac in queue:
        return False
    queue[dest_mac].put(data)
    return True


def get_from_queue(dest_mac):
    try:
        return dequeue(queue[dest_mac], timeout=2)
    except Empty:
        return None


def read_data():
    while True:
        data = tap.read(2 * tap.mtu)
        dest_mac = get_mac(data)
        put_in_queue(dest_mac, data)


def inner_application(env, start_response):
    global password
    try:
        if env['PATH_INFO'] == '/connect':
            msg = env['wsgi.input'].read().decode()
            org_mac = msg.split(" ", 1)[0]
            if msg.split(" ", 1)[1] != password:
                start_response('403 Forbidden', bytes(), [])
                return [b"bad password"]

            # Convert org_mac string to bytes
            try:
                client_mac = binascii.unhexlify(org_mac)
            except:
                client_mac = org_mac.encode() if isinstance(org_mac, str) else org_mac

            # Check if this client already has an IP
            if client_mac in ips:
                ip = ips[client_mac]
                if client_mac not in queue:
                    init_queue(client_mac)
            else:
                global ip_sequential
                ip = bytes(
                    bytearray(IP_PREFIX) + bytearray((ip_sequential // 256,
                                                      ip_sequential % 256)))
                ip_sequential += 1
                init_queue(client_mac)
                ips[client_mac] = ip
                save_mac_ip_map()

            f = open("/opt/oiproctor/log/httptun.log", "a")
            f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " " + org_mac + " -> " + binascii.hexlify(client_mac).decode('ascii') + " " + ".".join(map(str, ip)) + "\n")
            f.close()

            ips_text = ""
            for k, v in ips.items():
                ips_text = ".".join(map(str, v)) + " " + binascii.hexlify(k).decode('ascii') + "\n" + ips_text # We write it in reverse order so newest entries are on top of older ones
            f = open(VARRUNPATH, "w")
            f.write(ips_text)
            f.close()

            start_response('200 OK', ip, [])
            return [client_mac, ip]

        if env['PATH_INFO'] == '/send':
            client_mac = env['wsgi.input'].read(6)
            if client_mac not in queue:
                start_response('403 Forbidden', bytes(), [])
                return [b""]

            def process_packet(data):
                dest_mac = get_mac(data)
                if dest_mac == MYMAC or dest_mac == BROADCAST:
                    tap.write(data)
                if dest_mac != MYMAC:
                    put_in_queue(dest_mac, data)

            parse_packets(env['wsgi.input'], process_packet)
            start_response('200 OK', ips[client_mac], [])
            return []

        if env['PATH_INFO'] == '/recv':
            client_mac = env['wsgi.input'].read(6)
            if client_mac not in queue:
                start_response('403 Forbidden', bytes(), [])
                return [b""]
            data = get_from_queue(client_mac)
            if data is None or not data:
                start_response('204 No content', ips[client_mac], [])
                return [b'']
            start_response('200 OK', ips[client_mac], [])
            return [serialize_packets(data)]

        start_response('404 Not Found', bytes(),
                       [('Content-Type', 'text/html')])
        return [b'<h1>Not Found</h1>']
    except:
        traceback.print_exc()
        start_response('500', bytes(), [])
        return [b'Internal server error']


def application(env, real_start_response):
    answer_status = 0
    info = bytes()

    def start_response(status, client_info, hdrs):
        nonlocal answer_status
        nonlocal info
        answer_status = status
        info = client_info
        real_start_response(status, hdrs)

    start = datetime.datetime.now()
    data = inner_application(env, start_response)
    end = datetime.datetime.now()
    log_line = (env['REMOTE_ADDR'] + ": " + "%.5f" %
                ((end - start).total_seconds()) + " " + env['PATH_INFO'] +
                ' ' + str(answer_status))
    if len(info) == 4:
        log_line = log_line.ljust(50)
        log_line += " client ip: " + ".".join(map(str, info))
    print(log_line)
    return data


def main():
    global tap, password
    if len(sys.argv) != 2:
        print("Usage: %s password" % sys.argv[0])
        sys.exit(1)
    password = sys.argv[1]

    load_mac_ip_map()  # Load existing mappings on startup

    tap = TunTapDevice(flags=IFF_TAP)
    tap.addr = ".".join(map(str, IP_PREFIX + (0, 1)))
    tap.netmask = '255.255.0.0'
    tap.mtu = 1300
    tap.hwaddr = MYMAC
    tap.up()
    tap_reader = threading.Thread(target=read_data, daemon=True)
    tap_reader.start()
    varrundir = os.path.dirname(VARRUNPATH)
    if not os.path.exists(varrundir):
        os.makedirs(varrundir)
    open(VARRUNPATH, "w").close()
    print('Serving on 8088...')
    WSGIServer(application, port=8088, numthreads=1000).start()


if __name__ == '__main__':
    main()
