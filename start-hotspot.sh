#!/bin/bash
source /etc/profile.d/rpi_hotspot_env.sh
set -e
echo "[HOTSPOT] Starting $HOTSPOT_NAME (manual NM profile)"

nmcli networking on
nmcli radio wifi on

# Ensure $AP_WIRELESS_NIC is managed
nmcli dev set "$AP_WIRELESS_NIC" managed yes

# Remove old hotspot profile
nmcli connection delete "$HOTSPOT_NAME" 2>/dev/null || true

# Create AP connection WITHOUT shared IP
nmcli connection add \
  type wifi \
  ifname "$AP_WIRELESS_NIC" \
  con-name "$HOTSPOT_NAME" \
  autoconnect no \
  ssid "$HOTSPOT_NAME"

nmcli connection modify "$HOTSPOT_NAME" \
  802-11-wireless.mode ap \
  802-11-wireless.band bg \
  ipv4.method manual \
  ipv4.addresses 192.168.4.1/24 \
  ipv6.method ignore \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "$HOTSPOT_PWD"

# Bring it up
nmcli connection up "$HOTSPOT_NAME"

# Captive portal redirect
iptables -t nat -F
iptables -t nat -A PREROUTING -i "$AP_WIRELESS_NIC" -p tcp --dport 80 -j REDIRECT --to-port "$HOTSPOT_PORT"

echo "[HOTSPOT] $HOTSPOT_NAME is up"
