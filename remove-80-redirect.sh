#!/bin/bash
source /etc/profile.d/rpi_hotspot_env.sh
iptables -t nat -D PREROUTING -i "$AP_WIRELESS_NIC" -p tcp --dport 80 -j REDIRECT --to-port "$HOTSPOT_PORT"