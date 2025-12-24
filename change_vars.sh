#!/bin/bash
AP_WIRELESS_NIC="wlan0"
WIRELESS_CLIENT_NIC="wlan1"
HOTSPOT_PORT="8080"
TITLE_TEXT="Your Title Here"
GO_TO_BUTTON_TEXT="Go to Website"
HOTSPOT_NAME="RPi AP"
HOTSPOT_PWD="password"

SCRIPT_NAME="rpi_hotspot_env.sh"
echo "Creating system-wide environment script in /etc/profile.d..."
sudo tee /etc/profile.d/${SCRIPT_NAME} > /dev/null << EOF
export AP_WIRELESS_NIC="${AP_WIRELESS_NIC}"
export WIRELESS_CLIENT_NIC="${WIRELESS_CLIENT_NIC}"
export HOTSPOT_PORT="${HOTSPOT_PORT}"
export TITLE_TEXT="${TITLE_TEXT}"
export GO_TO_BUTTON_TEXT="${GO_TO_BUTTON_TEXT}"
export HOTSPOT_NAME="${HOTSPOT_NAME}"
export HOTSPOT_PWD="${HOTSPOT_PWD}"
EOF