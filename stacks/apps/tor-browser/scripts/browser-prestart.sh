#!/usr/bin/env bash
set -euo pipefail

readonly KASM_HOME="/home/kasm-user"
readonly VPN_HOST="tasks.tor-vpn"
readonly VPN_PORT=1080
readonly VPN_WAIT_TIMEOUT=300
readonly TORRC_DEFAULTS="${KASM_HOME}/tor-browser/tor-browser/Browser/TorBrowser/Data/Tor/torrc-defaults"
readonly XFCONF_DIR="${KASM_HOME}/.config/xfce4/xfconf"
readonly TOR_START="${KASM_HOME}/tor-browser/tor-browser/Browser/start-tor-browser"

install_dependencies() {
    local needed=()
    command -v xfce4-terminal &>/dev/null || needed+=(xfce4-terminal)
    if (( ${#needed[@]} == 0 )); then
        return
    fi
    echo "[PRESTART] Installing: ${needed[*]}"
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${needed[@]}"
}

wait_for_socks5() {
    local elapsed=0
    echo "[PRESTART] Waiting for ${VPN_HOST}:${VPN_PORT}..."
    until bash -c "cat < /dev/null > /dev/tcp/${VPN_HOST}/${VPN_PORT}" 2>/dev/null; do
        sleep 5
        elapsed=$(( elapsed + 5 ))
        if (( elapsed >= VPN_WAIT_TIMEOUT )); then
            echo "[PRESTART] ERROR: ${VPN_HOST}:${VPN_PORT} unreachable after ${VPN_WAIT_TIMEOUT}s." >&2
            exit 1
        fi
        if (( elapsed % 30 == 0 )); then
            echo "[PRESTART] Still waiting (${elapsed}s elapsed)..."
        fi
    done
    echo "[PRESTART] SOCKS5 ready (${elapsed}s)."
}

find_iptables() {
    local candidate
    for candidate in /usr/sbin/iptables-legacy /sbin/iptables-legacy; do
        if [[ -x "$candidate" ]]; then
            echo "$candidate"
            return
        fi
    done
    command -v iptables
}

apply_kill_switch() {
    local vpn_ip
    local subnet
    local ipt
    # Must resolve before iptables closes DNS access.
    vpn_ip=$(getent hosts "${VPN_HOST}" | awk '{print $1}' | head -1)
    subnet=$(awk -F. '{print $1"."$2"."$3".0/24"}' <<< "$vpn_ip")
    ipt=$(find_iptables)

    export XTABLES_LOCKFILE=/tmp/xtables.lock
    "$ipt" -F OUTPUT
    "$ipt" -A OUTPUT -o lo -j ACCEPT
    "$ipt" -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
    "$ipt" -A OUTPUT -d "$subnet" -j ACCEPT
    "$ipt" -A OUTPUT -j DROP
    echo "[PRESTART] Kill switch active (${subnet})."
}

configure_torrc() {
    mkdir -p "$(dirname "${TORRC_DEFAULTS}")"
    sed -i '/^Socks5Proxy/d' "${TORRC_DEFAULTS}" 2>/dev/null || true
    echo "Socks5Proxy ${VPN_HOST}:${VPN_PORT}" >> "${TORRC_DEFAULTS}"
    chown -R 1000:1000 "$(dirname "${TORRC_DEFAULTS}")"
    echo "[PRESTART] Socks5Proxy written to torrc-defaults."
}

configure_xfdesktop() {
    local xfconf_user="${XFCONF_DIR}/xfce-perchannel-xml/xfce4-desktop.xml"
    local xfconf_single="${XFCONF_DIR}/single-application-xfce-perchannel-xml/xfce4-desktop.xml"
    local f

    for f in "$xfconf_user" "$xfconf_single"; do
        if [[ -f "$f" ]]; then
            sed -i 's|name="style" type="int" value="0"|name="style" type="int" value="2"|g' "$f"
        fi
    done

    if [[ ! -f "$xfconf_user" ]]; then
        mkdir -p "$(dirname "$xfconf_user")"
        cat > "$xfconf_user" << 'XML'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="desktop-icons" type="empty">
    <property name="style" type="int" value="2"/>
  </property>
</channel>
XML
    fi
}

configure_proxy_env() {
    local marker="# tor-vpn socks5 proxy"
    local profile="${KASM_HOME}/.bashrc"
    if ! grep -q "$marker" "$profile" 2>/dev/null; then
        cat >> "$profile" << EOF

${marker}
export ALL_PROXY="socks5h://${VPN_HOST}:${VPN_PORT}"
export HTTPS_PROXY="socks5h://${VPN_HOST}:${VPN_PORT}"
export HTTP_PROXY="socks5h://${VPN_HOST}:${VPN_PORT}"
EOF
        echo "[PRESTART] Proxy env written to .bashrc."
    fi
}

write_desktop_icons() {
    mkdir -p "${KASM_HOME}/Desktop"
    local term
    if command -v xfce4-terminal &>/dev/null; then
        term="xfce4-terminal"
    else
        term="xterm"
    fi
    cat > "${KASM_HOME}/Desktop/terminal.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Terminal
Exec=${term}
Icon=utilities-terminal
Terminal=false
EOF
    chmod +x "${KASM_HOME}/Desktop/terminal.desktop"
    echo "[PRESTART] Terminal desktop icon written (${term})."
}

write_autostart() {
    mkdir -p "${KASM_HOME}/.config/autostart"

    # Remove stale autostart entries left on the iSCSI volume by older deployments.
    rm -f \
        "${KASM_HOME}/.config/autostart/trust-desktop-files.desktop" \
        "${KASM_HOME}/.config/autostart/thunar-daemon.desktop"

    cat > "${KASM_HOME}/.config/autostart/tor-browser.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Tor Browser
Exec=${TOR_START} --allow-remote --new-tab
Hidden=false
X-GNOME-Autostart-enabled=true
EOF

    # Ensure PulseAudio is running for KasmVNC audio streaming.
    cat > "${KASM_HOME}/.config/autostart/pulseaudio.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=PulseAudio
Exec=pulseaudio --start --daemonize
Hidden=false
X-GNOME-Autostart-enabled=true
EOF
}

patch_thunar_stub() {
    # xfdesktop 4.16 routes all desktop icon activations through the org.xfce.FileManager
    # D-Bus interface. kasmweb stubs /usr/bin/thunar as #!/bin/sh, so D-Bus activation
    # exits immediately and every desktop icon click fails with "This feature requires a
    # file manager service". Replace the stub with a minimal Python service implementing
    # Execute, Launch, and LaunchFiles.
    cat > /usr/bin/thunar << 'THUNAR_PY'
#!/usr/bin/env python3
import os, re, shlex, subprocess, configparser
from urllib.parse import unquote, urlparse
import dbus, dbus.service, dbus.mainloop.glib
from gi.repository import GLib

DBUS_NAME = "org.xfce.FileManager"
DBUS_PATH = "/org/xfce/FileManager"

def uri_to_path(uri):
    if uri.startswith("file://"):
        return unquote(urlparse(uri).path)
    return uri

def expand_exec(exec_str):
    return shlex.split(re.sub(r'%[a-zA-Z%]', '', exec_str).strip())

class FileManagerService(dbus.service.Object):
    def __init__(self, bus, path):
        super().__init__(bus, path)

    def _launch_desktop(self, path):
        cfg = configparser.ConfigParser(interpolation=None)
        cfg.read(path)
        if "Desktop Entry" not in cfg:
            return
        exec_str = cfg["Desktop Entry"].get("Exec", "")
        cmd = expand_exec(exec_str)
        if cmd:
            subprocess.Popen(cmd, start_new_session=True)

    def _open_path(self, path):
        if path.endswith(".desktop"):
            self._launch_desktop(path)
        else:
            subprocess.Popen(["xdg-open", path], start_new_session=True)

    # xfdesktop 4.16 calls Execute when activating desktop icons
    @dbus.service.method(DBUS_NAME, in_signature="ssasss", out_signature="")
    def Execute(self, working_directory, uri, files, display, startup_id):
        path = uri_to_path(uri)
        if not os.path.isabs(path):
            path = os.path.join(working_directory or ".", path)
        self._open_path(path)

    @dbus.service.method(DBUS_NAME, in_signature="sss", out_signature="")
    def Launch(self, uri, display, startup_id):
        self._open_path(uri_to_path(uri))

    @dbus.service.method(DBUS_NAME, in_signature="sasss", out_signature="")
    def LaunchFiles(self, working_directory, filenames, display, startup_id):
        for filename in filenames:
            path = uri_to_path(filename)
            if not os.path.isabs(path):
                path = os.path.join(working_directory or ".", path)
            self._open_path(path)

def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    dbus.service.BusName(DBUS_NAME, bus)
    FileManagerService(bus, DBUS_PATH)
    GLib.MainLoop().run()

if __name__ == "__main__":
    main()
THUNAR_PY
    chmod +x /usr/bin/thunar
    ln -sf /usr/bin/thunar /usr/bin/Thunar
    echo "[PRESTART] org.xfce.FileManager D-Bus service installed at /usr/bin/thunar."
}

patch_custom_startup() {
    # kasmweb's service manager monitors custom_startup.sh and restarts it when
    # it exits. With DISABLE_CUSTOM_STARTUP set the original exits immediately,
    # causing "Unknown Service" spam. This version sleeps to keep the service alive.
    cat > /dockerstartup/custom_startup.sh << 'CUSTOM'
#!/usr/bin/env bash
START_COMMAND="$HOME/tor-browser/tor-browser/Browser/start-tor-browser"
PGREP="firefox.real"
ARGS=${APP_ARGS:---allow-remote --new-tab --detach}
if [[ -n "${DISABLE_CUSTOM_STARTUP:-}" ]]; then
    while true; do sleep 60; done
fi
while true; do
    if ! pgrep -x "$PGREP" > /dev/null; then
        $START_COMMAND $ARGS
    fi
    sleep 1
done
CUSTOM
    chmod +x /dockerstartup/custom_startup.sh
}

main() {
    install_dependencies
    wait_for_socks5
    apply_kill_switch
    configure_torrc
    configure_xfdesktop
    configure_proxy_env
    write_autostart
    write_desktop_icons
    patch_thunar_stub
    patch_custom_startup

    chown -R 1000:1000 "${KASM_HOME}" 2>/dev/null || true

    exec su -s /bin/bash kasm-user -c \
        "exec /dockerstartup/kasm_default_profile.sh /dockerstartup/vnc_startup.sh /dockerstartup/kasm_startup.sh"
}

main
