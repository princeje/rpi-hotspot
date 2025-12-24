#!/usr/bin/env python3

import subprocess
import time
import socket
import threading
from flask import Flask, request, render_template, redirect, jsonify
import os
from typing import Optional
import socket
from pathlib import Path

# Get the absolute path of the script file itself
script_path = Path(__file__).resolve()
project_root_path = script_path.parent
hostname = socket.gethostname()

def load_env_file(path="/etc/profile.d/rpi_hotspot_env.sh"):
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            if "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k.strip(), v)

def get_env_var(name: str, default: Optional[str] = None) -> str:
    """
    Helper function to get an environment variable with optional default.
    Raises an error if the variable is required but missing.
    """
    
    load_env_file()  # Load env file to ensure variables are set

    value = os.getenv(name, default)
    if value is None:
        raise EnvironmentError(f"Required environment variable '{name}' is not set.")
    return value

app = Flask(
    __name__,
    static_folder=f"{project_root_path}/captive_static/static",
    static_url_path="/static",
    template_folder=project_root_path / "templates"
)

# stop_server = False


# -----------------------
# Helpers
# -----------------------

def run(cmd):
    print(" ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True)


def has_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False


def get_connected_ssid_and_ipv4(nic: str):
    """
    Return a tuple (ssid, ipv4) for the active connection on the given
    wireless interface `nic`. Returns (None, None) on failure or if not connected.
    """
    try:
        # Find active connection bound to this device
        out = subprocess.check_output([
            "nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"
        ]).decode()
        conn_name = None
        for line in out.splitlines():
            if not line:
                continue
            parts = line.split(":", 1)
            if len(parts) != 2:
                continue
            name, device = parts
            if device == nic:
                conn_name = name
                break

        ssid = conn_name
        if conn_name:
            try:
                ssid_out = subprocess.check_output([
                    "nmcli", "-t", "-f", "802-11-wireless.ssid", "connection", "show", conn_name
                ]).decode().strip().split(':')[1]
                if ssid_out:
                    ssid = ssid_out
            except Exception:
                pass

        # Get IPv4 address for the interface
        ip = None
        try:
            ip_out = subprocess.check_output(["ip", "-4", "-o", "addr", "show", "dev", nic]).decode()
            for line in ip_out.splitlines():
                parts = line.split()
                if "inet" in parts:
                    idx = parts.index("inet")
                    ip = parts[idx + 1].split("/")[0]
                    break
        except Exception:
            ip = None

        return ssid, ip
    except Exception:
        return None, None
    return False

def nmcli(cmd):
    return subprocess.check_output(["nmcli"] + cmd).decode()


# -----------------------
# WiFi scanning
# -----------------------

def scan_wifi():
    try:
        output = nmcli(["-f", "IN-USE,SSID", "dev", "wifi", "list"])
        ssids = []
        for line in output.splitlines()[1:]:
            ssid = line.strip().lstrip("*").strip()
            if ssid:
                ssids.append(ssid)
        return sorted(set(ssids))
    except Exception as e:
        print("Scan failed:", e)
        return []


# -----------------------
# WiFi connect
# -----------------------

def connect_wifi(ssid, password):
    if not ssid:
        return False, "No SSID selected"

    if password:
        result = run([
            "nmcli", "dev", "wifi", "connect", ssid,
            "password", password,
            "ifname", f"{WIRELESS_CLIENT_NIC}"
        ])
    else:
        result = run([
            "nmcli", "dev", "wifi", "connect", ssid,
            "ifname", f"{WIRELESS_CLIENT_NIC}"
        ])

    if result.returncode != 0:
        print("Connection failed:", result.stderr)
        return False, result.stderr.strip() or "Connection failed"

    for _ in range(20):
        if has_internet():
            print("Connected to WiFi with internet")
            return True, "Connected successfully"
        
        time.sleep(2)

    return False, "Connected to AP, but no internet detected"


# -----------------------
# Hotspot control
# -----------------------

def start_hotspot():
    run(["./start-hotspot.sh"])


def stop_hotspot():
    # global stop_server
    run(["./stop-hotspot.sh"])
    # stop_server = True


def wait_for_AP_NIC(timeout=100):
    start = time.time()
    while time.time() - start < timeout:
        try:
            state = subprocess.check_output(
                ["nmcli", "-t", "-f", "DEVICE,STATE", "device"]
            ).decode()
            for line in state.splitlines():
                if line.startswith(f"{AP_WIRELESS_NIC}:"):
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


# -----------------------
# Flask captive portal
# -----------------------

CAPTIVE_PATHS = [
    "/generate_204",
    "/hotspot-detect.html",
    "/connecttest.txt",
    "/check_network_status.txt",
    "/ncsi.txt",
    "/success.txt"
]

# Add captive portal detection routes
@app.route("/generate_204")
@app.route("/hotspot-detect.html")
@app.route("/connecttest.txt")
@app.route("/check_network_status.txt")
@app.route("/ncsi.txt")
@app.route("/success.txt")
def captive_check():
    # Always return the portal page instead of expected response
    ssids = scan_wifi()
    options = "".join(f'<option value="{s}">{s}</option>' for s in ssids)
    
    if has_internet():
        connected_ssid, client_ip = get_connected_ssid_and_ipv4(WIRELESS_CLIENT_NIC)
    else:
        connected_ssid, client_ip = None, None

    context = {
        'ssids': ssids,
        'options': options,
        'title_text': TITLE_TEXT,
        'hostname': hostname,
        'hotspot_port': HOTSPOT_PORT,
        'go_to_button_text': GO_TO_BUTTON_TEXT,
        'status': None,           # or some message
        'status_type': "info",  # or 'danger', etc.
        'connected_ssid': connected_ssid,
        'client_ip': client_ip,
    }

    print(context)

    return render_template("index.html", **context)

@app.route('/remove-80-redirect', methods=['GET', 'HEAD'])
def remove_80_redirect():
    # Your Python function
    redirect_result = redirect(f"http://{hostname}.local", code=302)
    run(["./remove-80-redirect.sh"])    
    # Redirect to some URL
    return redirect_result


@app.route('/forget-connection', methods=['POST'])
def forget_connection():
    data = None
    try:
        data = request.get_json(force=True)
    except Exception:
        data = request.form or {}

    conn = None
    if isinstance(data, dict):
        conn = data.get('conn') or data.get('connection')

    if not conn:
        return jsonify({'success': False, 'message': 'No connection name provided'}), 400

    try:
        result = run(["nmcli", "connection", "delete", conn])
        if result.returncode != 0:
            return jsonify({'success': False, 'message': result.stderr.strip() or 'Failed to delete connection'}), 500
        else:            
            run(["./add-80-redirect.sh"])
            start_hotspot()
        return jsonify({'success': True, 'message': f'Connection "{conn}" removed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# This ensures any unknown URL opens the portal:
@app.route("/<path:path>")
def catch_all(path):

    # Let Flask serve static files normally
    # (otherwise /static/bootstrap.min.css is redirected to the webpage)
    if path.startswith("static/"):
        return app.send_static_file(path.replace("static/", "", 1))
    
    
    ssids = scan_wifi()
    options = "".join(f'<option value="{s}">{s}</option>' for s in ssids)
    if has_internet():
        connected_ssid, client_ip = get_connected_ssid_and_ipv4(WIRELESS_CLIENT_NIC)
    else:
        connected_ssid, client_ip = None, None

    context = {
        'ssids': ssids,
        'options': options,
        'title_text': TITLE_TEXT,
        'hostname': hostname,
        'hotspot_port': HOTSPOT_PORT,
        'go_to_button_text': GO_TO_BUTTON_TEXT,
        'status': None,           # or some message
        'status_type': "info",  # or 'danger', etc.
        'connected_ssid': connected_ssid,
        'client_ip': client_ip,
    }

    print(context)

    return render_template("index.html", **context)


@app.route("/", methods=["GET", "POST"])
def index():
    ssids = scan_wifi()
    options = "".join(f'<option value="{s}">{s}</option>' for s in ssids)

    status = None
    status_type = "info"

    if request.method == "POST":
        ssid = request.form.get("ssid")
        password = request.form.get("psk", "")

        success, message = connect_wifi(ssid, password)
        if success:
            threading.Timer(3.0, stop_hotspot).start()
            status = message
            status_type = "success"
        else:
            status = message
            status_type = "danger"

    if has_internet():
        connected_ssid, client_ip = get_connected_ssid_and_ipv4(WIRELESS_CLIENT_NIC)
    else:
        connected_ssid, client_ip = None, None

    context = {
        'ssids': ssids,
        'options': options,
        'title_text': TITLE_TEXT,
        'hostname': hostname,
        'hotspot_port': HOTSPOT_PORT,
        'go_to_button_text': GO_TO_BUTTON_TEXT,
        'status': status,           # or some message
        'status_type': status_type,  # or 'danger', etc.
        'connected_ssid': connected_ssid,
        'client_ip': client_ip,
    }

    print(context)

    return render_template("index.html", **context)


def run_flask():
    app.run(host="0.0.0.0", port=HOTSPOT_PORT, threaded=True, use_reloader=False)

# ----------------------------
# Main loop
# ----------------------------

if __name__ == "__main__":
    
    # Load the hotspot configuration from environment variables
    # These should be exported by /etc/profile.d/rpi_hotspot_env.sh when running under a shell
    # that sources profile.d (or manually sourced)
    RPI_HOTSPOT_VER = get_env_var("RPI_HOTSPOT_VER")
    AP_WIRELESS_NIC = get_env_var("AP_WIRELESS_NIC")
    WIRELESS_CLIENT_NIC = get_env_var("WIRELESS_CLIENT_NIC")
    HOTSPOT_PORT = get_env_var("HOTSPOT_PORT")
    TITLE_TEXT = get_env_var("TITLE_TEXT")
    GO_TO_BUTTON_TEXT = get_env_var("GO_TO_BUTTON_TEXT")

    # Optional: Convert port to int if you'll use it numerically
    try:
        HOTSPOT_PORT_INT = int(HOTSPOT_PORT)
    except ValueError:
        raise ValueError(f"HOTSPOT_PORT must be a valid integer, got: {HOTSPOT_PORT}")
    
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    time.sleep(10)
    wait_for_AP_NIC()
  
    while True:
        print("Checking device connection status...")
        # If WIRELESS_CLIENT_NIC is not connected to a wifi and has no internet
        ssid_ip = get_connected_ssid_and_ipv4(WIRELESS_CLIENT_NIC)
        if isinstance(ssid_ip, tuple):
            ssid, ip = ssid_ip
        else:
            ssid, ip = (None, None)

        if (not ssid and not ip) and not has_internet():
            print(f"{WIRELESS_CLIENT_NIC} not connected and no internet, starting hotspot")
            start_hotspot()
        else:
            print(f"{WIRELESS_CLIENT_NIC} connected or has internet, stopping hotspot")
            # stop_hotspot()                      

        # Wait before checking again
        time.sleep(150)
