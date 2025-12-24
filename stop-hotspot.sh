#!/bin/bash
source /etc/profile.d/rpi_hotspot_env.sh
set -e

echo "[HOTSPOT] Stopping $HOTSPOT_NAME"

iptables -t nat -F
nmcli connection down "$HOTSPOT_NAME" 2>/dev/null || true
nmcli connection delete "$HOTSPOT_NAME" 2>/dev/null || true

nmcli networking on
nmcli dev set "$AP_WIRELESS_NIC" managed yes
iptables -t nat -D PREROUTING -i "$AP_WIRELESS_NIC" -p tcp --dport 80 -j REDIRECT --to-port "$HOTSPOT_PORT"


echo "[HOTSPOT] Client mode restored"
