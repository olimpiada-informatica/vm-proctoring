# Technical Reference: vm-proctoring

This document is intended for IT staff as an operational reference for preparing new contest setups or config changes during live contests. It covers the full internals of how the proctor server and contestant VMs interact.

---

## 1. Architecture Overview

```
Contestant laptop
 └── VirtualBox / VMware / etc.
      └── Xubuntu 24.04 VM (vm-contestant scripts)
           ├── Firefox (contestant works here)
           ├── dns-lockdown (iptables firewall)
           ├── httptun client (TAP tunnel to OI Proctor over HTTPS)
           └── oiproctor_monitor (status OSD, loop reporting to OI Proctor via TAP tunnel)
Contest server (Docker container, vm-proctor)
 ├── nginx (TLS termination + reverse proxy)
 ├── httptun server (Python, TAP endpoint, port 8088, sitting behind nginx on port 443)
 ├── oiproctor_users_monitor (Node.js, status/alerts/CMS, port 81, sitting behind nginx on port 443)
 ├── dnsmasq (internal DNS for tunnel network)
 ├── shellinabox (web terminal at /admin, port 4200, sitting behind nginx on port 443)
 └── oiproctor (bash CLI for remote control of contestant VMs)
```

All VM–proctor communication goes through a TAP-over-HTTP tunnel (`httptun`). The tunnel creates a private virtual Ethernet network (`10.9.0.0/16`). The proctor server is always `10.9.0.1`. Each VM gets a unique IP in that range, assigned by MAC address.

---

## 2. Repository Layout

```
vm-proctoring/
├── vm-contestant/           # Files to install on each contestant VM
│   ├── etc/
│   │   ├── oisetup/profiles/oi      # Example contest profile
│   │   └── systemd/system/          # Systemd service units
│   └── usr/local/
│       ├── bin/                     # User-facing utilities
│       └── sbin/                    # Admin/daemon scripts
└── vm-proctor/              # Docker setup for the proctor server
    ├── docker-compose.yml
    └── oiproctor/
        ├── Dockerfile
        ├── bin/                     # Server-side scripts
        ├── etc/                     # Config + credentials
        ├── log/                     # Persisted logs (survives container restart)
        └── run/                     # Runtime state (survives container restart, empty for fresh restart)
```

---

## 3. Proctor Server (Docker)

### 3.1 Container Startup

The container uses **supervisord** as PID 1 (`/opt/oiproctor/etc/supervisord.conf`). The programs started, in order:

| Program                   | Purpose                                                                   |
|---------------------------|---------------------------------------------------------------------------|
| `oiproctor_init.sh`       | First-run credential bootstrap                                            |
| `oiproctor start 3`       | httptun server (waits 3s for init)                                        |
| `oiproctor_users_monitor` | CMS users status + alerts web server                                      |
| `nginx`                   | TLS + reverse proxy to httptun, `oiproctor_users_monitor` and shellinabox |
| `shellinabox`             | Web terminal on `/admin`                                                  |
| `dnsmasq-refresh`         | Restarts dnsmasq periodically to keep it updated with /etc/hosts          |

**`oiproctor_init.sh`** runs once at every container start (not just first) and:
1. Patches `/etc/resolv.conf` to use `127.0.0.1` instead of Docker's internal resolver `127.0.0.11`, so dnsmasq handles all DNS.
2. Creates `/opt/oiproctor/etc/tunnel.pwd` if missing — from `TUNNEL_PASS` env var or a random 44-char string printed to stdout. **This password must match `PROCTOR_TUNNEL_PASSWORD` in the VM profile.**
3. Creates `/opt/oiproctor/etc/vmkey.pwd` (RSA keypair) if missing — from `VM_SSH_PASS` env var or auto-generated. **The public key (`vmkey.pwd.pub`) must be copied to `/home/oi/.ssh/authorized_keys` on every VM.**
4. Creates `/opt/oiproctor/etc/proctor.pwd` if missing — from `OIPROCTOR_PASS` env var or random. Sets the shellinabox password (Linux's `proctor` user password, via `chpasswd`).

All three credential files persist across container restarts (`stop`/`start`) because they live in the image's filesystem (not in a volume), but do not persist across re-builds (they are not stored in a mounted volume).

### 3.2 nginx Routing

All external traffic hits nginx on port 443 (HTTPS). Routes:

| Path prefix                                | Proxied to       | Handled by                 |
|--------------------------------------------|------------------|----------------------------|
| `/connect`, `/send`, `/recv`               | `127.0.0.1:8088` | httptun server (Python)    |
| `/status`, `/update`, `/alerts`, `/notify` | `127.0.0.1:81`   | users monitor (Node.js)    |
| `/admin`                                   | `127.0.0.1:4200` | shellinabox (web terminal) |
| Everything else                            | HTTP 444         | nginx                      |

TLS certificates are in `oiproctor/etc/https/fullchain.pem` and `privkey.pem`. The repo includes self-signed certificates; replace them with real ones if necessary, or use reverse proxy with valid certificates on the host. The VM client calls with `ignorecert` so the tunnel works even with self-signed certificates.

### 3.3 httptun Server (`bin/httptun/server.py`)

A Python WSGI server running on port 8088 that implements a TAP-over-HTTP tunnel.

**Config**: configured via `/opt/oiproctor/etc/httptun`. This file is reread during execution when SIGHUP is received.

**TAP device**: created at startup as `tap0`, address `10.9.0.1/16`, hardware address `ter000`.

**Three HTTP endpoints**:

- **`/connect`** (POST): Body is `<mac_hex> <password>`. Validates password. If the MAC is already known, restores its previously assigned IP. Otherwise allocates the next sequential IP (`10.9.0.2`, `10.9.0.3`, …). Saves the MAC→IP mapping to `/opt/oiproctor/run/connections` (hosts-file format: `ip mac`). Returns the 6-byte MAC and 4-byte IP the client must use for the TAP link.
- **`/send`** (POST): First 6 bytes of body are the client MAC. Remaining bytes are serialised Ethernet frames. Frames destined for `ter000` or broadcast are written to the TAP device; all others are routed to the target MAC's queue.
- **`/recv`** (POST): First 6 bytes are the client MAC. Dequeues buffered frames for that client (2-second timeout). Returns 204 if empty, 200 with frame data otherwise.

**IP persistence across proctor restarts**: `load_ips()` reads `connections` on startup and restores the full MAC→IP map. The sequential counter resumes from the highest IP seen.

**Log**: every `/connect` request is appended to `/opt/oiproctor/log/httptun.log` with `timestamp remote_ip org_mac -> canonical_mac tunnel_ip`.

### 3.4 Users Monitor (`bin/oiproctor_users_monitor`)

A Node.js HTTP server on port 81 with an in-memory `users_map` of `{ips: {ip: {username, ip, timestamp}}, usernames: {username: ip}}`. On startup it tries to reload this map from `/opt/oiproctor/run/users`.

**Four endpoints**:

- **`GET /update?<contest_id>_login=<username>`**: Called every 5 seconds by each VM's `oiproctor_monitor`. Updates `users_map` in memory. Writes users_map to `run/users`. Sends SIGHUP to dnsmasq. Raises an alert if a known IP switches usernames, or if a known user appears from a new IP. Only accepts requests from IPs matching `^10\.9\.` (tunnel IPs only).
- **`GET /status`**: HTML status page. Shows all `CMS_USERS` as colored boxes: **green** (updated within `2 × ping_interval` seconds), **yellow** (seen before but not recently), **red** (never seen). Cached for `ping_interval/2` seconds.
- **`GET /alerts`**: HTML page listing all alert messages (screen changes, disk warnings, IP switches, etc.) with timestamps.
- **`GET /notify?msg=<text>`**: Adds an alert message from a VM. Only accepts tunnel IPs. Only accepts requests from IPs matching `^10\.9\.` (tunnel IPs only).

### 3.5 dnsmasq

Configured via `/etc/dnsmasq.d/oiproctor` to serve as the internal DNS resolver and to load three additional hosts files:

| File                             | Format     | Content                                           |
|----------------------------------|------------|---------------------------------------------------|
| `/opt/oiproctor/run/connections` | `ip mac`   | MAC addresses as hostnames for tunnel IPs         |
| `/opt/oiproctor/run/alias`       | `ip alias` | Human-readable aliases set with `oiproctor alias` |
| `/opt/oiproctor/run/users`       | `ip user`  | CMS usernames as hostnames for tunnel IPs         |

`dnsmasq-refresh` is a shell loop that HUPs dnsmasq every 60 seconds to pick up file changes. `oiproctor_users_monitor` also HUPs dnsmasq immediately on each user update.

Because dnsmasq is also the container's local resolver (`/etc/resolv.conf` is patched to point to `127.0.0.1`), external DNS queries are forwarded to the upstream server defined at build time (`NAME_SERVER` build arg, default `8.8.8.8`).

### 3.6 `oiproctor` CLI (`bin/oiproctor`)

The main control tool, invoked from the shellinabox web terminal at `/admin`. Requires destination as second argument (IP, tunnel short-form like `0.5`, tunnel mac address, CMS username, or `all`).

**Server-side commands** (no VM contact):

| Command                   | Effect                                                               |
|---------------------------|----------------------------------------------------------------------|
| `start`                   | Start httptun server in foreground                                   |
| `stop`                    | Kill the running httptun server process                              |
| `status`                  | Check if httptun server is running                                   |
| `letin <true|false>`      | Allow/disallow new devices to join the tunnel                        |
| `log`                     | Show full connection history from `httptun.log`                      |
| `active`                  | List connected VMs (MAC + IP) from `connections` + `alias` files     |
| `ignore <ip>`             | Exclude an IP from `active` listings (e.g. old/stale entries)        |
| `alias <ip> <name>`       | Assign a friendly name to an IP (persists to `alias` file)           |
| `aliases`                 | List all manually assigned aliases                                   |
| `users`                   | Lists all known CMS users and their tunnel IPs                       |
| `whois <ip\|user\|short>` | Reverse/forward lookup: maps between tunnel IP, MAC, CMS user, alias |

**Client-side commands** (commands that SSH into VMs using `parallel-ssh`/`scp`):

| Command                          | Effect                                                                              |
|----------------------------------|-------------------------------------------------------------------------------------|
| `ping <dest>`                    | Ping VM(s), report alive/dead                                                       |
| `ssh <dest>`                     | Open interactive SSH session (destination `all` not accepted)                       |
| `put <dest> <path>`              | Copy file/directory to VM(s) into contestant account's home directory               |
| `get <dest> <path>`              | Download file/directory from VM(s) into `oiproctor_get_<timestamp>/`                |
| `allow <dest> <domain\|ip>`      | Add domain/IP to DNS allowlist on VM(s)                                             |
| `block <dest> <domain\|ip>`      | Remove from DNS allowlist on VM(s)                                                  |
| `addhost <dest> <hostname> <ip>` | Add to `/etc/hosts` and allowlist on VM(s)                                          |
| `delhost <dest> <hostname>`      | Remove from `/etc/hosts` on VM(s)                                                   |
| `disk <dest>`                    | Obtain VM's disk usage                                                              |
| `uptime <dest>`                  | Obtain VM's uptime/CPU load                                                         |
| `mem <dest>`                     | Obtain VM's available memory                                                        |
| `lock <dest>`                    | Logs out and locks the VM (restart lightdm, disable guest login, show lock message) |
| `unlock <dest>`                  | Disable locked status (re-enable guest login, restart lightdm)                      |
| `tell <dest> <text>`             | Show info dialog (zenity) on VM screen                                              |
| `alert <dest> <text>`            | Show red warning dialog on VM screen                                                |
| `yesno <dest> <text>`            | Show yes/no dialog, prints YES or NO                                                |
| `ask <dest> <text>`              | Show text entry dialog, prints response                                             |
| `clean <dest>`                   | Kill all open zenity dialogs on VM                                                  |
| `reset <dest>`                   | Restart lightdm (resets the contestant's user session)                              |
| `diff <dest>`                    | List files added by the contestant to the home directory                            |
| `cmd <dest> <...>`               | Run an arbitrary command on VM(s)                                                   |
| `version <dest>`                 | Print VM version (`/etc/vm_version`)                                                |

SSH uses key-based auth (`vmkey.pwd` on the proctor, corresponding public key in `/home/oi/.ssh/authorized_keys` on VMs). `StrictHostKeyChecking=no` is used since tunnel IPs may be reassigned. All SSH sessions are recorded by `log-session` to `/opt/oiproctor/log/ssh/`.

---

## 4. Contestant VM

### 4.1 oisetup and Profiles

`oisetup` is the main setup script, run as root. It idempotently configures the VM from a profile file in `/etc/oisetup/profiles/`.
º
**Invocations**:
- `sudo oisetup <profilename>` — full setup: installs packages, sets locale, configures all features, cleans browser history/logs.
- `sudo oisetup` — refresh mode: re-applies the current (`default`) profile without clearing contestant data or running `host_cleanup`.
- `sudo oisetup_config [-r <prop>] [-u <prop> <val>] [-f]` — read/update a single property in the profile. With `-f`, immediately re-runs `oisetup` after the edit.

**What `oisetup` configures** (in order):
1. Sets password for the native proctor user (`oi`) if `NATIVE_PROCTOR_SHADOW` is set.
2. Installs/uninstalls APT and pip packages.
3. Installs locales, sets default locale and keyboard layout.
4. Enables/disables LightDM guest session (`40-enable-guest.conf`).
5. Disables screen lock (`98noscreenlock` in X session).
6. Sets up persistent storage (`/var/guest-data/` + fstab for USB if `PERSISTENT_EXTERNAL=true`).
7. Writes Firefox policies (`/etc/firefox/policies/policies.json`): homepage, bookmarks, extensions, DNS-over-HTTPS disabled.
8. Sets logo (symlink in `/usr/share/plymouth/themes/xubuntu-logo/`).
9. Writes the lock screen message to `/etc/oisetup/lock_message.conf`.
10. Enables/disables the httptun client (`/etc/httptun` config, systemd services).
11. Sets static `/etc/hosts` entries (these entries are `# OISETUP` tagged).
12. Enables/disables DNS lockdown.
13. Saves the VM version timestamp to `/etc/vm_version`.
14. Updates the `default` symlink in profiles to point to this profile.

**Profile location**: `/etc/oisetup/profiles/`. The active profile is the file that `default` symlinks to. An example profile is at `vm-contestant/etc/oisetup/profiles/oi`.

**Implicit DNS allowlist additions**: `oisetup` builds `dns_lockdown_implicit_exceptions` as it processes settings — the proctor URL, contest URL, bookmark domains, and static host IPs are all automatically added to the allowlist before DNS lockdown is applied.

### 4.2 httptun Client

**Configuration file**: `/etc/httptun`
```bash
ENABLED=1         # 0 to disable entirely
SERVER="https://proctor.example.com"
PASSWORD="<tunnel password>"
```
This file is written by `oisetup` (permissions `600`).

**Flow**:
1. At boot, `httptun-launch.service` (`Restart=always`) calls `httptun-launch`, which reads `/etc/httptun` and runs `/usr/local/sbin/httptun/client.py`.
2. `client.py` checks for `/tmp/tap0cache` (6-byte MAC + 4-byte IP, written on first successful connect). If present, it reuses that identity without a new `/connect` call — this means restarting the service within the same session doesn't change the tunnel IP.
3. If no cache, reads the VM's MAC from `/etc/oisetup/oiproctor_mac.installed` (created by `/usr/local/sbin/oiproctor_mac`), POSTs `<mac_hex> <password>` to `/connect`, and receives its client MAC + IP to use in future exchanges inside the tunnel.
4. Creates a TAP device `tap0` configured with the assigned IP and `255.255.0.0` netmask.
5. Spawns a sender thread (TAP → POST `/send`) and a receiver loop (POST `/recv` → TAP).
6. On HTTP 403, removes `/tmp/tap0cache` and exits, triggering a service restart (which will re-register).

**`httptun-keepalive.service`**: pings `10.9.0.1` every 20 seconds, waiting for 10 seconds each time. If 3 consecutive failures happen (90 seconds downtime), restarts `httptun-launch.service`. This auto-reconnects the tunnel if the proctor server restarts or the connection drops.

### 4.3 MAC Generation and Tunnel IP Persistence

The MAC address is the **identity** that the proctor uses to track a VM and preserve its tunnel IP across reconnections.

**`oiproctor_mac`** (runs once at boot via `oiproctor_mac.service`):
1. Reads the VM's hardware UUID via `get_vm_uuid` (`dmidecode --type system`).
2. Reads the stored UUID from `/etc/oisetup/uuid.installed` and the stored MAC from `/etc/oisetup/oiproctor_mac.installed`.
3. **If UUID matches**: keeps the existing MAC. Same import = same MAC.
4. **If UUID differs**: clears the MAC (the VM was re-imported/cloned), triggering generation of a new random MAC.
5. Validates the MAC: rejects all-zeros, all-`FF`, and MACs with an odd second nibble (multicast bit). Regenerates until valid.
6. Writes the new MAC to `/etc/oisetup/oiproctor_mac.installed` and the current UUID to `/etc/oisetup/uuid.installed`.

**Consequence for tunnel IPs**:
- VM **reboots** → same UUID → same MAC → proctor server restores same tunnel IP (if server's `connections` file has not been cleared).
- VM **re-imported/cloned** → new UUID → new random MAC → new tunnel IP.

### 4.4 oiproctor_monitor

A bash loop running every 5 seconds (`oiproctor_monitor.service`). Provides the on-screen display (OSD) and reports status to the proctor server via HTTP over the tunnel.

**OSD**: Uses `osd_cat` to display `<mac_hex> <tunnel_ip_last_two_octets>` at the top center of the screen in grey. While the VM is not yet connected to the tunnel (no `tap0` IP), only the MAC is shown. The overlay auto-refreshes every 60 seconds.

**Reporting to proctor** (all requests go to `http://10.9.0.1/notify` or `/update`):

| Event                    | Endpoint                                | Method | Condition                         |
|--------------------------|-----------------------------------------|--------|-----------------------------------|
| Screen resolution change | `/notify?msg=<old> > <new> <uptime>`    | POST   | When `xrandr` output changes      |
| Disk space alert         | `/notify?msg=<df line>`                 | POST   | When a partition exceeds 95% full |
| CMS user login           | `/update?<contest_id>_login=<username>` | POST   | Every 5s if a user is logged in   |

**CMS user detection** (`get_cms_user`):
1. Reads `/etc/oisetup/cms_contest_id.installed` for the contest ID string (written by `oisetup`).
2. Looks in the contestant's Firefox profile directory (`/home/contestant/.mozilla/firefox/*.default-release/`).
3. First tries to read the `<contest_id>_login` cookie from `cookies.sqlite` (via `sqlite3`).
4. Falls back to reading from `sessionstore-backups/recovery.jsonlz4` (via `lz4jsoncat` + `jq`).
5. The cookie value is base64-encoded JSON; extracts the username field.

### 4.5 DNS Lockdown

An iptables-based firewall that restricts all outbound traffic to a domain/IP allowlist. Managed by two components:

**`dns-lockdown` script** (`/usr/local/sbin/dns-lockdown`):

Config files in `/etc/dns-lockdown/`:
- `config`: `ENABLED=1|0` and `INTERFACE=<iface>` (default `en+`, from `oisetup`)
- `domains.allowlist`: one domain per line (written by `oisetup` or `dns-lockdown allow/block`)
- `ips.allowlist`: one IP or CIDR per line (written by `oisetup` or `dns-lockdown allow/block`)

`start` action:
1. Sets default policy `DROP` on all chains (INPUT, FORWARD, OUTPUT) for IPv4 and IPv6.
2. Accepts ICMP (ping/traceroute).
3. Accepts loopback.
4. Accepts all traffic on `tap0` (proctor tunnel is always reachable).
5. For each domain in `domains.allowlist`: adds an iptables rule matching the domain name as a hex string in outbound UDP port-53 packets (DNS queries). This allows the query but not yet the response (it is allowed in step 7).
6. Creates/populates an `ipset` named `allowlist_ips` with all IPs from `ips.allowlist`, adds iptables rules to accept traffic to/from those IPs.
7. Accepts ESTABLISHED/RELATED connections.

`stop` action: flushes all iptables rules and chains, resets policies to ACCEPT.

`allow <domain|ip>...`: adds domain/IP/CIDR to the appropriate allowlist file, then restarts the firewall.

`block <domain|ip>...`: removes the domain/IP/CIDR from the appropriate file, then restarts the firewall.

**`dns-lockdown-monitor`** (`/usr/local/sbin/dns-lockdown-monitor`):
- Runs `tcpdump` on port 53, watching for DNS response packets.
- Parses the source IP from each response line.
- Calls `ipset add allowlist_ips <ip>` for each resolved IP.
- This is the mechanism that makes domain whitelisting work dynamically: when a DNS query for an allowed domain returns an IP, that IP is immediately added to `allowlist_ips`, allowing the subsequent HTTPS connection.

**Systemd services**:
- `dns-lockdown.service`: `Type=oneshot; RemainAfterExit=yes`. Runs `dns-lockdown start` on service start, `dns-lockdown stop` on service stop. Enabled at boot by `oisetup`.
- `dns-lockdown-monitor.service`: `Restart=on-failure`. Runs the tcpdump monitor. Enabled at boot by `oisetup`.

**What is always whitelisted** (built into `oisetup`):
- `NATIVE_DNS_LOCKDOWN` list (Firefox/Ubuntu services like `fonts.googleapis.com`, `detectportal.firefox.com`, `addons.mozilla.org`, `connectivity-check.ubuntu.com`, etc.)
- The proctor server's domain (from `PROCTOR_TUNNEL_URL`)
- The contest URL's domain (from `CONTEST_URL`)
- All bookmark domains (from `BOOKMARKS`)
- All static host IPs (from `STATIC_HOSTS`)

### 4.6 Session Management

**Guest session**: LightDM is configured with `allow-guest=true; autologin-guest=true`. The guest session uses `/etc/guest-session/skel/` as the home skeleton. All data is wiped when the guest logs out — the contestant always starts fresh.

**Persistent storage** (`/var/guest-data/`): if `PERSISTENT_STORAGE=true`, a symlink `~/oie` (or configured `PERSISTENT_DIRNAME`) is placed in the guest skel pointing to `/var/guest-data/`. This directory has ACLs granting full access to all its files and directories recursively to all users, so future guest logins (ie. VM reboot) maintain read/write access to its contents. If `PERSISTENT_EXTERNAL=true`, `/dev/sdb1` (USB stick) is mounted on `/var/guest-data/` via fstab (with `nofail`), so persistance of files can be guaranteed through VM corruption.

The contestant's home is `/home/contestant`, which is a symlink managed by LightDM's guest session mechanism (`/etc/guest-session/prefs.sh`). The actual session directory is a temporary directory that LightDM creates at login.

**VM Lock/Unlock**: `oiproctor lock` works by renaming config files:
- Moves `40-enable-lock-message.conf.disable` → `40-enable-lock-message.conf` (shows the lock message at the greeter)
- Moves `40-enable-guest.conf` → `40-enable-guest.conf.disable` (disables guest auto-login)
- Restarts lightdm

When locked, the `lock_message.sh` script is configured as the greeter's session and loops calling `zenity` to show the lock message. `oiproctor unlock` reverses the file renames and restarts lightdm.

---

## 5. Inter-System Communication Summary

```
VM (10.9.0.2-10.9.255.254)                                         Proctor server (10.9.0.1)
────────────────────────────────────────────────────────────────────────────────────────────
httptun client       ──HTTP POST /connect,/send,/recv───────────▶  httptun server
                                                                   (TAP, 10.9.0.0/16)

oiproctor_monitor    ──HTTP GET /update?<contest>_login=<user>──▶  users_monitor
                     ──HTTP GET /notify?msg=<msg>───────────────▶  users_monitor (alerts)

oiproctor (via SSH)  ◀──parallel-ssh/scp─────────────────────────  oiproctor CLI
   dns-lockdown
   static_hosts
   lightdm control
   zenity dialogs
   df/uptime/free
```

All VM→proctor traffic uses HTTP (unencrypted) over the tunnel interface (`tap0`). The tunnel itself is encrypted at the HTTPS level. The proctor→VM direction uses SSH (`oi` user, `vmkey.pwd` private key, `/home/oi/.ssh/authorized_keys` public key).

---

## 6. Persistence Matrix

This table answers "does this change survive X?" — the most critical reference for live operations.

| Setting / State                                                | VM reboot                                          | `oisetup` re-run                       | OI Proctor container restart                          |
|----------------------------------------------------------------|----------------------------------------------------|----------------------------------------|-------------------------------------------------------|
| Profile settings (DNS, URLs, etc.)                             | **Yes**                                            | **No** (overwritten)                   | N/A                                                   |
| `dns-lockdown allow/block` changes                             | **Yes** (edited allowlist files)                   | **No** (oisetup rewrites the files)    | N/A                                                   |
| `dns-lockdown start/stop` (iptables state)                     | **No** (service re-applies on boot)                | **No**                                 | N/A                                                   |
| `static_hosts -u/-d` changes                                   | **Yes** (edits `/etc/hosts`)                       | **No** (oisetup rewrites hosts)        | N/A                                                   |
| Tunnel enabled/disabled (`/etc/httptun`)                       | **Yes**                                            | **No** (oisetup rewrites it)           | N/A                                                   |
| Tunnel MAC (`oiproctor_mac.installed`)                         | **Yes** (same UUID)                                | **Yes**                                | N/A                                                   |
| Tunnel IP assignment on proctor                                | **Yes** (if proctor server is still up)            | **Yes**                                | **Yes** (unless `run/connections` is cleared)         |
| CMS user→IP mapping                                            | **Yes** (monitor re-reports)                       | **Yes**                                | **Yes** (unless `run/users` is cleared)               |
| Lock/Unlock state (lightdm conf files)                         | **Yes**                                            | **No** (oisetup runs `lock_cleanup`)   | N/A                                                   |
| Persistent storage contents                                    | **Yes**                                            | **No** (except with refresh mode `-r`) | N/A                                                   |
| Session data (contestant files)                                | **No** (wiped on guest logout)                     | N/A                                    | N/A                                                   |
| Proctor credentials (`tunnel.pwd`, `vmkey.pwd`, `proctor.pwd`) | N/A                                                | N/A                                    | **Yes** (files in image, not in volume)               |
| Proctor logs (`log/`)                                          | N/A                                                | N/A                                    | **Yes** (volume mount)                                |
| Proctor settings (`run/`)                                      | N/A                                                | N/A                                    | **Yes** (volume mount)                                |

---

## 7. Key Configuration Files

### 7.1 On the VM

| File                                    | Purpose                             | Written by                            |
|-----------------------------------------|-------------------------------------|---------------------------------------|
| `/etc/oisetup/profiles/<name>`          | Contest profile                     | IT staff                              |
| `/etc/oisetup/profiles/default`         | Symlink to active profile           | `oisetup`                             |
| `/etc/httptun`                          | Tunnel server URL + password        | `oisetup`                             |
| `/etc/oisetup/oiproctor_mac.installed`  | VM's tunnel MAC address             | `oiproctor_mac` (at boot)             |
| `/etc/oisetup/uuid.installed`           | VM UUID for MAC binding             | `oiproctor_mac` (at boot)             |
| `/etc/oisetup/cms_contest_id.installed` | CMS contest short name              | `oisetup`                             |
| `/etc/oisetup/lock_message.conf`        | Lock screen message text            | `oisetup`                             |
| `/etc/dns-lockdown/config`              | DNS lockdown enabled + interface    | `oisetup`                             |
| `/etc/dns-lockdown/domains.allowlist`   | Whitelisted domains                 | `oisetup`, `dns-lockdown allow/block` |
| `/etc/dns-lockdown/ips.allowlist`       | Whitelisted IPs                     | `oisetup`, `dns-lockdown allow/block` |
| `/etc/hosts`                            | Static name resolutions             | `oisetup`, `static_hosts`             |
| `/etc/firefox/policies/policies.json`   | Firefox managed policy              | `oisetup`                             |
| `/home/oi/oiproctor_diff.ignore`        | Regexp list for `oiproctor diff`    | `oisetup`                             |
| `/home/oi/.ssh/authorized_keys`         | SSH public key for proctor access   | IT staff (at VM prep)                 |
| `/etc/vm_version`                       | Timestamp of last `oisetup` run     | `vm_version_update`                   |
| `/tmp/tap0cache`                        | Cached tunnel MAC+IP (session only) | `httptun/client.py`                   |

### 7.2 On the Proctor Server

| File                                | Purpose                        | Written by                | Used by                                     |
|-------------------------------------|--------------------------------|---------------------------|---------------------------------------------|
| `oiproctor/etc/config`              | Default config values          | IT staff                  | `oiproctor_users_monitor`, `oiproctor`      |
| `oiproctor/etc/httptun`             | httptun config values          | IT staff, `oiproctor`     | `httptun`                                   |
| `oiproctor/etc/tunnel.pwd`          | Tunnel shared password         | `oiproctor_init.sh`       | `httptun`                                   |
| `oiproctor/etc/vmkey.pwd`           | SSH private key for VM access  | `oiproctor_init.sh`       | SSH                                         |
| `oiproctor/etc/proctor.pwd`         | Web terminal password          | `oiproctor_init.sh`       | shellinabox                                 |
| `oiproctor/etc/https/*.pem`         | TLS certificate + key          | IT staff                  | nginx                                       |
| `oiproctor/run/connections`         | MAC→IP map (hosts format)      | `httptun/server.py`       | dns, `httptun`, `oiproctor`                 |
| `oiproctor/run/users`               | CMS user→IP map (hosts format) | `oiproctor_users_monitor` | dns, `oiproctor_users_monitor`, `oiproctor` |
| `oiproctor/run/alias`               | IP→alias map (hosts format)    | `oiproctor alias`         | `oiproctor`                                 |
| `oiproctor/log/httptun.log`         | Full connection history        | `server.py`               |                                             |
| `oiproctor/log/oiproctor_users.log` | CMS user activity + alerts     | `oiproctor_users_monitor` |                                             |
| `oiproctor/log/ssh/`                | SSH session transcripts        | `log-session`             |                                             |
| `.env`                              | Build-time + runtime overrides | IT staff                  |                                             |

---

## 8. Operational Procedures

### 8.1 Preparing a new contest

1. Edit `vm-proctor/.env` with the contest's `TUNNEL_PASS`, `CMS_CONTEST_SHORTNAME`, `CMS_USERS`, etc.
2. `docker compose build oiproctor` — must rebuild after `.env` changes.
3. Delete all files from `oiproctor/run/` if starting fresh.
4. `docker compose up -d oiproctor`
5. On first run, check container logs for the generated tunnel password and SSH public key:
   ```
   docker compose logs oiproctor | grep -A2 'PROCTOR_TUNNEL_PASSWORD\|authorized_keys'
   ```
6. On each VM: create profile with that password in `PROCTOR_TUNNEL_PASSWORD`. Place the SSH public key in `/home/oi/.ssh/authorized_keys`. Run `sudo oisetup <profile>`.

### 8.2 Hot-swapping a profile setting during a live contest

To change a setting (e.g. add a bookmark or change a URL) without clearing contestant data:

```bash
# On the VM (or via oiproctor cmd):
sudo oisetup_config -u BOOKMARKS '("example.com" "Example")' -f
# -f triggers oisetup in refresh mode (no data wipe)
```

Or edit the profile file directly and run `sudo oisetup` (no profile argument = refresh mode).

**Important**: `oisetup` resets the DNS allowlist from scratch on every run. Any `dns-lockdown allow` changes made via `oiproctor allow` are lost. Re-add them via `oiproctor allow all <domain>` after the oisetup run, or add them to `DNS_LOCKDOWN_ALLOWLIST` in the profile.

### 8.3 Adding a domain to the allowlist across all VMs mid-contest

```bash
# From the oiproctor web terminal (/admin):
oiproctor allow all example.com
```

This runs `dns-lockdown allow example.com` via SSH on every connected VM simultaneously. Changes persist through VM reboots but NOT through the next `oisetup` run.

### 8.4 Logging out and locking and unlocking all VMs simultaneously

```bash
oiproctor lock all    # Logs out and disables guest login, restarts lightdm
oiproctor unlock all  # Re-enables guest login, restarts lightdm
```

The lock message text is configured in the profile (`LOCK_MESSAGE_BODY`) and written to `/etc/oisetup/lock_message.conf` by `oisetup`. It can be changed live by writing that file directly.

### 8.5 Identifying which contestant is at which VM

```bash
oiproctor whois 10.9.0.5      # IP → CMS username + aliases
oiproctor whois user01        # CMS username → IP
oiproctor active              # Show all connected VMs (MAC + IP)
oiproctor users               # Show CMS user state
```

Or check the `/status` page for a visual colour-coded overview.

### 8.6 Uploading file to contestant's home folder in a VM

```bash
oiproctor put <ip> <local_file>
```

### 8.7 Downloading contestant code from a VM

```bash
oiproctor get <ip> /home/contestant/oi/
# Creates ./oiproctor_get_TIMESTAMP/<ip>/ with the contents
```

### 8.8 Cleaning up between two contest sessions

On each VM:
```bash
clean_persistent_dir   # Wipes /var/guest-data/
```
Or from the proctor:
```bash
oiproctor reset all    # Wipes VMs' /var/guest-data/ and restarts lightdm (kills active sessions)
```

### 8.9 Managing static hosts on a VM

Add a static host:
```bash
oiproctor addhost <ip> <host_name> <host_ip>
```

Remove a static host:
```bash
oiproctor delhost <ip> <host_name\|host_ip>
```

### 8.10 Obtaining root access on a VM

First, access `oi` account access.

- Remotely, from the proctor: `oiproctor ssh <ip>`
- From the VM within the contestant's account: `su oi`

Once as `oi`: `sudo -s`


---

## 9. Common Issues

**VM shows MAC but no tunnel IP suffix in OSD**: The httptun client has not connected yet or is failing. Check:
- Check that httptun client is running in thee VM. If it is not, run `httptun-launch` as root in the VM.
- That `PROCTOR_TUNNEL_PASSWORD` in the profile matches `tunnel.pwd` on the proctor server.
- That the proctor URL is reachable from the VM (it must be whitelisted in the DNS lockdown — `oisetup` does this automatically for `PROCTOR_TUNNEL_URL`).

**VM reconnects and gets a new tunnel IP after proctor restart**: Unexpected behaviour — Either the VM's oiproctor MAC changed, the VM's UUID changed (the VM was re-imported), or the proctor's `run/connections` is not on a persistent volume. Use `oiproctor alias` to assign stable names to IPs.

**`oiproctor active` shows stale entries**: Use `oiproctor ignore <ip>` to suppress them, or delete `run/connections` and restart the httptun server (`oiproctor stop && oiproctor start`).

**CMS users not appearing on `/status`**: Verify the `CMS_CONTEST_SHORTNAME` matches exactly the `Name` field of the contest in CMS (case-sensitive). Verify `CMS_USERS` lists the exact usernames. The monitor only accepts updates from `10.9.x.x` IPs, so the tunnel must be active. Check `log/oiproctor_users.log` for activity.

**DNS lockdown is too restrictive after oisetup**: Some required IPs may not be pre-resolvable at oisetup time (dynamic CDNs, etc.). Add them with `oiproctor allow all <domain>` or add to `DNS_LOCKDOWN_ALLOWLIST` in the profile.

**`oiproctor diff` reports unexpected files**: The diff ignore list is set by `PROCTOR_DIFF_IGNORE` in the profile (appended to a long built-in list). Patterns are regexps matched against relative paths within `/home/contestant/`. Add patterns to suppress known benign files.
