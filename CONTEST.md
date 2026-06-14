# Contest Operations Guide

This document covers how to run a fraud-proof contest with this system — from preparation weeks in advance through teardown. It addresses both technical procedures and the human proctoring that the technology cannot replace.

## Understanding the Threat Model

Before following any procedure, understand what can and cannot be cheated, and how.

### What the system prevents automatically (when correctly configured)
- Accessing the internet beyond the approved allowlist (DNS lockdown + iptables), including DNS tunneling, etc.
- Accessing email, messaging, or social media during the contest.
- Carrying browser history or downloaded material into the session (guest session wipes everything on logout).
- A contestant logging into CMS under another contestant's credentials.
- A contestant using the host computer (leaving or resizing the VM)..

### What requires active human proctoring
- Phones, tablets, smartwatches, earphones, smartglasses or secondary laptops brought into the room.
- Contestants reading from printed notes or books (unless explicitly allowed).
- Verbal communication between contestants.
- A contestant physically showing their screen to another.
- Impersonation: someone other than the registered contestant sitting at the machine.
- BIOS-level bypass: booting a different OS from USB if the BIOS is not locked.
- A contestant with sufficient technical knowledge attempting to disable the guest session or by-pass the DNS lockdown (ie. by accessing the VM's `oi` account).

### What generates an automatic alert (visible on the proctor server's `/alerts` page)
- A known CMS user logging in from a new tunnel IP (could mean they reconnected or moved machines).
- Two different CMS usernames appearing from the same tunnel IP (two people sharing one VM).
- Screen resolution change (external display connected, or VM resized).
- VM disk usage exceeding 95%.

## 1. Preparation (Weeks Before the Contest)

### 1.1 Configure the Contestants' VM

1. Edit `/etc/oisetup/profiles/<profilename>` on the VM master image.

Some critical settings:
| Setting                   | Use                                                                          |
|---------------------------|------------------------------------------------------------------------------|
| `GUEST_SESSION`           | Clean slate per contestant                                                   |
| `DNS_LOCKDOWN`            | Block internet                                                               |
@ `DNS_LOCKDOWN_ALLOWLIST`  | Additional domains to allow                                                  |
| `PERSISTENT_EXTERNAL`     | Support persistent dir through VM corruption by saving to external USB drive |
| `NATIVE_PROCTOR_SHADOW`   | Shadow hash of `oi` account's password, must be a strong password            |
| `PROCTOR_TUNNEL_PASSWORD` | Tunnel password (for proctoring), must match proctor server's                |
| `CONTEST_URL`             | CMS's URL                                                                    |

The `oi` account inside the VM has passwordless sudo, which means a contestant who knows its password can disable the DNS lockdown, or anything else. **The password must be unknown to contestants.** Do **not** share the `oi` account's password with anyone (neither proctots), only IT staff should know it. Generate `NATIVE_PROCTOR_SHADOW` value with `openssl passwd -6 -salt $(openssl rand -hex 8) <password>`

2. Run `sudo oisetup <profilename> -d`. Then shut down the VM.

3. From the host run `vboxmanage modifymedium --compact ./disk.vdi` (or the equivalent for your VM software).

4. Export the VM using OVF 1.0 format, without manifest file.

5. Distribute the exported VM image to all exam sites.

### 1.2 Configure the Proctor Server

1. Create `vm-proctor/.env`:
   ```
   TUNNEL_PASS=<same as PROCTOR_TUNNEL_PASSWORD in profile>
   OIPROCTOR_PASS=<strong password for /admin web terminal>
   USERS_MONITOR_TITLE=<Contest name>
   VM_DIALOG_TITLE=<Contest name>
   CMS_CONTEST_SHORTNAME=<exact "Name" field from CMS contest config>
   CMS_USERS=user01 user02 user03 ...  # All registered contestant usernames
   CONTESTANTS_CIDR=<ip_range>  # Only these IPs will be allowed to connect with the oiproctor. Leave empty to allow all
   ```

2. `docker compose build oiproctor` — must rebuild after any `.env` change.

3. Replace `oiproctor/etc/https/fullchain.pem` and `privkey.pem` with a real certificate (or contestants' browsers will warn them and may behave unexpectedly with DNS-over-HTTPS fallback).

4. Empty the directories `oiproctor/run/` and  `oiproctor/log/` to reset state.

5. `docker compose up -d oiproctor` to start the server. On first run, check logs:
   ```bash
   docker compose logs oiproctor
   ```
   Note the SSH public key printed and copy it to `/home/oi/.ssh/authorized_keys` on the VM master image.

### 1.3 Test

Do a full dry run with two test VMs:
- Start both VMs, confirm both appear in `oiproctor active`.
- Open `/status` on the proctor server — both should appear.
- Log into CMS with a test user from each VM — both should turn green on `/status`.
- Try `oiproctor tell all "Test message"` — confirm it appears on both screens.
- Try `oiproctor lock all` and `oiproctor unlock all` — confirm all VMs are logged out and locked, then unlocked.
- Confirm a non-whitelisted domain is blocked and a whitelisted domain works.
- Try rebooting one VM — confirm it reconnects automatically.

---

## 2. Day of the Contest

### 2.1 Before Contestants Arrive

- Assign one proctor per 15 contestants onsite or 8 contestants online.
- One person should be dedicated to watching the `/status` and `/alerts` pages throughout the contest (they do nothing else).
- Brief all proctors on: contestants should have the VM on fullscreen, never leave the VM, contestants should not have more than one display.
- If the venue provides the computers, ensure each seat has exactly one display, one keyboard and one mouse (no extras).
- Assign seats: define a seating plan, ensure contestants who know each other are not seated adjacent.

### 2.2 Admitting Contestants

At the door, before anyone enters:

1. **Verify identity**: check a government-issued photo ID against the list of registered contestants. Do not rely on contest registration cards alone.

2. **Confiscate electronic devices**: phones, tablets, smartwatches, earbuds, smartglasses. Place in labelled envelopes kept at the front desk. This is non-negotiable — a device found on a contestant during the contest will mean immediate desqualification.

In the contest room:

1. **No bags at the desk**: only the items provided (pencil, scratch paper if allowed) go to the seat. Coats go on a coat rack, not draped over chairs.

2. **Take seats**: use a pre-assigned seating plan. Do not let contestants choose their own seats.

3. **Announce the rules**:
```
- Welcome to [Contest Name]. Before we begin, please listen to the following rules.
- The virtual machine in front of you has been configured for this contest. It gives you access only to the contest platform and the documentation resources listed in the browser bookmarks. All other internet access is blocked.
- The use of any electronic device other than the VM is strictly prohibited. This includes phones, tablets, smartwatches, smartglasses and earbuds. If you have any of these devices, surrender them now.
- You may not communicate with other contestants during the contest, verbally or in writing. If you need to ask something, raise your hand and a proctor will come to you.
- You are not allowed to interact with your computer's host operating system. You may only use the virtual machine.
- All activity on the virtual machines is monitored, and we are notified if anything unusual happens.
- All the work saved to the [contest] directory is kept within sessions. Do not save files outside that folder — they will not survive a crash.
- If you experience a technical problem — the screen freezes, the VM crashes, Firefox stops working — raise your hand immediately.
- The contest will last [N] hours and [M] minutes. We will announce when 30 minutes remain and when time is up
- Do you have any questions about the rules? … [Pause] … The contest will begin in [X] minutes."

```

4. Contestants import a new instance of th VM. This generates a new tunnel MAC for each contestant, different to any previous ones they had used.

5. Contestants boot their VMs and log into CMS. No other actions are allowed.

6. Checking all contestants are running the latest VM version:
```bash
oiproctor version all
```

7. Watch `/status` — as contestants log into CMS, their boxes should turn green within 5–10 seconds.
- **Green box** = contestant logged into CMS, VM reporting in normally.
- **Yellow box** = contestant was logged in but the VM has not reported in the last ~2 minutes. May mean the VM crashed or disconnected. Investigate.
- **Red box** = contestant never logged in from within the VM. Either a late arrival, a technical issue, they have not yet authenticated to CMS, or they are not logged into CMMS from within the VM. Investigate.

8. Once all the contestants are ready, disable new devices from connecting to the tunnel:
```bash
oiproctor letnew false
```
9. Checking only contestant VMs are connected to the tunnel (they should match the IPs in `/status`, and no duplicate users should have been reported in `/alerts`):
```bash
oiproctor active
```

10. Checking contestants have not done any actions beyond logging into CMS:
```bash
oiproctor diff all
```

### 2.3 Starting the Contest

When the start time arrives:

1. **Announce start**: "The contest begins now."

2. Monitor `/alerts`
- **Alert: "Known IP switched user"**: the same VM is now reporting a different CMS username. This is suspicious. Immediately check the physical seat.
- **Alert: "Known user found in new IP"**: a CMS user appears from a different tunnel IP than before. Could be a corrupt VM that had to be re-imported, or a different VM or machine (suspicious). Check the seat.
- **Alert: screen resolution change**: a contestant may have left the VM's fullscreen mode to interact with the host operating system. Check the seat.
- **Alert: disk space >95%**; Notify the contestant to prevent data loss.
- The `/status` page displays a user's IP when leaving the cursor for 1 second over a tile.

### 2.4 During the Contest

**IT operator (dedicated to the proctor console):**

- Keep monitoring `/alerts` at all times.
- If a VM has issues, root access may be needed. First, obtain `oi` account access, it can be accessed remotely with `oiproctor ssh <ip>` or in the VM from the contestant's account with `su oi`. Then `sudo -s` to gain superuser privileges.
- If a contestant VM has to be recreated, it will be a new device in the contest. Re-enable new devices to connect to the tunnel with:
```bash
oiproctor letnew true
```

**Physical proctors:**

- Walk the room continuously. Never stand still in one spot for more than 2 minutes.
- Look at screens, not at contestants' faces. You are checking what is on the screen.
- Anything other than the contest CMS and the allowed documentation in Firefox is a violation.
- Anything other than the virtual machine in fullscreen mode is a violation. Easily recognize the virtual machine is in fullscreen mode because it displays the tunnel's MAC and last two bytes of its IP at the top of the screen, report if anything else is displayed.
- Any visible phone or other device not allowed at the desk is a violation, even if it appears to be unused.
- If a contestant requests to leave (bathroom), one proctor must accompany them and ensure they do not access any devices (Wi-Fi/GSM/Bluetooth frequency detectors are encouraged).
- Do not answer questions about contest problems. Say: "I cannot help with that, it is part of the contest."
- Do not leave the room unattended at any point. There must always be at least one proctor physically present.

**At the 30-minute warning:**
```
- Thirty minutes remaining.
```

**If a VM crashes or disconnects** (disappears from `oiproctor active`):
- Dispatch a proctor to the seat.
- Have the contestant restart the VM. It will reconnect automatically.
- The contestant's work in the persistent directory survives a crash. If the VM got corruptes and must be re-imported, the persistent directory's data will only prevail if `PERSISTENT_EXTERNAL=true` and a USB drive was plugged and linked to the VM.
- The contestant must log in again into CMS.
- Log the incident: seat number, time, contestant name, nature of the issue.

### 2.5 Ending the Contest

1. **Announce end**:
```
- Time is up.
```

2. If one or more contestants have extra time, request all contestants remain seated and silent until the last contestant's contest time is over.

3. Return confiscated devices to contestants as they leave — one at a time, after verifying identity.

## 3. Multiple Contest Sessions (Same Day)

If the contest has two sessions, between sessions:

**On the proctor server, remotely:**

1. Clean on every VM the persistent directory and resets the user session: `oiproctor reset all`

**On the VMs, if remote procedure fails:**

1. Clean the persistent directory `clean_persistent_dir`

2. Restart the VM.

**Repeat the contestant admission procedure** from Section 2.2. Do not skip identity verification.