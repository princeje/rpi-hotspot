
#!/bin/bash
RPI-HOTSPOT_VER="0.1.0"
AP_WIRELESS_NIC="wlan0"
WIRELESS_CLIENT_NIC="wlan1"
HOTSPOT_PORT="8080"
TITLE_TEXT="Your Title Here"
GO_TO_BUTTON_TEXT="Go to Website"
HOTSPOT_NAME="RPi AP"
HOTSPOT_PWD="password"
# -------------------------------- USER CONFIGURATION ABOVE THIS LINE --------------------------------
#
# DO NOT CHANGE BELOW THIS LINE UNLESS YOU KNOW WHAT YOU ARE DOING!
#
# ----------------------------------------------------------------------------------------------------
SERVICE_FILE="/etc/systemd/system/rpi-hotspot-manager.service"

SCRIPT_NAME="rpi_hotspot_env.sh"
# touch /etc/profile.d/${SCRIPT_NAME}

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

sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install iw dnsmasq python3-flask -y

# Create the file with the specified content
SCRIPT_DIR=$(dirname $(realpath "${BASH_SOURCE:-$0}"))
touch $SERVICE_FILE
sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=RPi WiFi Hotspot Manager with Captive Portal
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/rpi_hotspot_manager.py
WorkingDirectory=${SCRIPT_DIR}

Restart=always
RestartSec=15

User=root
Group=root

StandardOutput=journal
StandardError=journal

TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions
chmod 644 "$SERVICE_FILE"

echo "Service file written to $SERVICE_FILE"

sudo tee /etc/dnsmasq.conf > /dev/null << EOF
interface=${AP_WIRELESS_NIC}
dhcp-range=192.168.4.10,192.168.4.50,255.255.255.0,1h
address=/#/192.168.4.1
EOF


# Enable Rpi Hotspot on next boot!
sudo systemctl daemon-reload
sudo systemctl enable dnsmasq
sudo systemctl enable rpi-hotspot-manager.service

