#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${HOME}/.local/opt/ak680-controller"; BIN_DIR="${HOME}/.local/bin"; TMP_DIR="$(mktemp -d)"
cleanup(){ rm -rf "$TMP_DIR"; }; trap cleanup EXIT
if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then gh repo clone hasiiib/Ajazz-AK680MAX-controller "$TMP_DIR/repo" -- --depth 1
else git clone --depth 1 https://github.com/hasiiib/Ajazz-AK680MAX-controller.git "$TMP_DIR/repo" 2>/dev/null || { echo "Clone failed. If private, run gh auth login."; exit 1; }; fi
mkdir -p "$APP_DIR" "$BIN_DIR"
find "$APP_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
cp -a "$TMP_DIR/repo/app/." "$APP_DIR/"; cp "$TMP_DIR/repo/requirements.txt" "$APP_DIR/"
python3 -m venv "$APP_DIR/.venv"; "$APP_DIR/.venv/bin/pip" install --upgrade pip >/dev/null
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
cat > "$BIN_DIR/ak680-controller" <<'LAUNCH'
#!/usr/bin/env bash
exec "$HOME/.local/opt/ak680-controller/.venv/bin/python" "$HOME/.local/opt/ak680-controller/main.py" "$@"
LAUNCH
chmod +x "$BIN_DIR/ak680-controller"; mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/ak680-controller.desktop" <<DESKTOP
[Desktop Entry]
Name=AK680 Controller
Comment=AJAZZ AK680 MAX keyboard utility
Exec=$BIN_DIR/ak680-controller
Icon=input-keyboard
Terminal=false
Type=Application
Categories=Utility;
DESKTOP
echo "Installed/updated AK680 Controller. Launch: ak680-controller"
