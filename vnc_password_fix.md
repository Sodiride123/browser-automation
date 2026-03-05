Here's the permanent fix — the two changes needed in /etc/supervisor/conf.d/supervisord.conf:

1. Disable vnc_setup (the password generator)

Find the [program:vnc_setup] block and add autostart=false so it stops generating a random password on startup.

2. Change x11vnc to -nopw

In the [program:x11vnc] command line, replace:
-rfbauth /root/.vnc/passwd
with:
-nopw

3. Reload supervisor
supervisorctl reread
supervisorctl update
supervisorctl restart x11vnc