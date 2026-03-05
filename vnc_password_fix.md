# VNC Password Fix — Permanent Solution

## Overview
Two changes are needed in `/etc/supervisor/conf.d/supervisord.conf` to disable VNC password authentication permanently.

---

## Step 1 — Disable `vnc_setup` (the password generator)

Add `autostart=false` to the `[program:vnc_setup]` block so it stops generating a random password on startup.

**Run this command:**
```bash
sed -i 's/\[program:vnc_setup\]/[program:vnc_setup]\nautostart=false/' /etc/supervisor/conf.d/supervisord.conf
```

> ⚠️ Note: The block already contains `autorestart=false` — this step adds the separate `autostart=false` key, which is different.

---

## Step 2 — Change x11vnc to use `-nopw`

In the `[program:x11vnc]` command line, replace `-rfbauth /root/.vnc/passwd` with `-nopw`.

**Run this command:**
```bash
sed -i 's/-rfbauth \/root\/.vnc\/passwd/-nopw/' /etc/supervisor/conf.d/supervisord.conf
```

---

## Step 3 — Verify the changes

Check that both changes were applied correctly:

```bash
# Verify autostart=false is in vnc_setup block
grep -n -A 8 "\[program:vnc_setup\]" /etc/supervisor/conf.d/supervisord.conf

# Verify -nopw is in x11vnc command
grep -n "nopw" /etc/supervisor/conf.d/supervisord.conf
```

Expected output for x11vnc should contain:
```
x11vnc -display :99 -forever -shared -nopw -rfbport 5901
```

---

## Step 4 — Reload supervisor

```bash
supervisorctl reread
supervisorctl update
supervisorctl restart x11vnc
```

Expected output:
```
vnc_setup: changed
x11vnc: changed
vnc_setup: stopped
vnc_setup: updated process group
x11vnc: stopped
x11vnc: updated process group
x11vnc: stopped
x11vnc: started
```

---

## Quick Run (All Steps at Once)

```bash
sed -i 's/\[program:vnc_setup\]/[program:vnc_setup]\nautostart=false/' /etc/supervisor/conf.d/supervisord.conf && \
sed -i 's/-rfbauth \/root\/.vnc\/passwd/-nopw/' /etc/supervisor/conf.d/supervisord.conf && \
supervisorctl reread && \
supervisorctl update && \
supervisorctl restart x11vnc
```

---

## Result
- `vnc_setup` will no longer run on startup (no more random password generation)
- `x11vnc` will run without password authentication (`-nopw`)
- VNC is accessible on port `5901` without a password