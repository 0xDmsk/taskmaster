#!/bin/sh
set -eu

DISPLAY_NUM="${DISPLAY:-:99}"
SCREEN_GEOMETRY="${XVFB_SCREEN_GEOMETRY:-1600x1000x24}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"

find_novnc_web_root() {
  for dir in /usr/share/novnc /usr/share/novnc/utils/novnc_proxy /usr/local/share/novnc; do
    if [ -d "$dir" ]; then
      echo "$dir"
      return 0
    fi
  done
  return 1
}

cleanup() {
  status=$?
  kill "${WEBSOCKIFY_PID:-}" "${X11VNC_PID:-}" "${FLUXBOX_PID:-}" "${XVFB_PID:-}" 2>/dev/null || true
  wait "${WEBSOCKIFY_PID:-}" "${X11VNC_PID:-}" "${FLUXBOX_PID:-}" "${XVFB_PID:-}" 2>/dev/null || true
  exit "$status"
}

trap cleanup INT TERM EXIT

Xvfb "$DISPLAY_NUM" -screen 0 "$SCREEN_GEOMETRY" -ac +extension RANDR &
XVFB_PID=$!

sleep 1

fluxbox >/tmp/fluxbox.log 2>&1 &
FLUXBOX_PID=$!

x11vnc -display "$DISPLAY_NUM" -rfbport "$VNC_PORT" -forever -shared -nopw -quiet >/tmp/x11vnc.log 2>&1 &
X11VNC_PID=$!

NOVNC_WEB_ROOT="$(find_novnc_web_root)"
websockify --web="$NOVNC_WEB_ROOT" "0.0.0.0:${NOVNC_PORT}" "127.0.0.1:${VNC_PORT}" >/tmp/websockify.log 2>&1 &
WEBSOCKIFY_PID=$!

exec python /usr/local/bin/playwright-operator
