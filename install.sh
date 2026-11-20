#!/usr/bin/env bash
set -Eeuo pipefail

REPO="https://github.com/hasiiib/Ajazz-AK680MAX-controller.git"
APP_NAME="ak680-controller"
OPT_DIR="${HOME}/.local/opt"
APP_DIR="${OPT_DIR}/${APP_NAME}"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${HOME}/.local/share/applications"
CONFIG_DIR="${HOME}/.config/${APP_NAME}"
WORK_DIR=""
STAGE_DIR=""
BACKUP_DIR=""
SWAPPED=0

say() { printf '\n[AK680] %s\n' "$*"; }
fail() { printf '\n[AK680] ERROR: %s\n' "$*" >&2; exit 1; }
cleanup() {
  local status=$?
  if [[ -n "$STAGE_DIR" && -d "$STAGE_DIR" ]]; then rm -rf -- "$STAGE_DIR"; fi
  if [[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR" ]]; then
    if (( SWAPPED == 0 )) && [[ ! -e "$APP_DIR" ]]; then mv -- "$BACKUP_DIR" "$APP_DIR" || true
    else rm -rf -- "$BACKUP_DIR"; fi
  fi
  if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then rm -rf -- "$WORK_DIR"; fi
  exit "$status"
}
trap cleanup EXIT

[[ "$(uname -s)" == "Linux" ]] || fail "This installer supports Linux/Ubuntu only."
command -v git >/dev/null || fail "Git is required. Install it with: sudo apt install git"
command -v python3 >/dev/null || fail "Python 3 is required. Install it with: sudo apt install python3 python3-venv"
python3 -m venv --help >/dev/null 2>&1 || fail "Python venv support is missing. Install it with: sudo apt install python3-venv"

mkdir -p -- "$OPT_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$CONFIG_DIR"
[[ ! -L "$APP_DIR" ]] || fail "Refusing to replace a symbolic link at $APP_DIR. Please inspect it first."
if [[ -e "$APP_DIR" && ! -d "$APP_DIR" ]]; then fail "$APP_DIR exists but is not a directory."; fi

WORK_DIR="$(mktemp -d)"
STAGE_DIR="${OPT_DIR}/.${APP_NAME}-staging-$$"
BACKUP_DIR="${OPT_DIR}/.${APP_NAME}-backup-$$"
[[ ! -e "$STAGE_DIR" && ! -e "$BACKUP_DIR" ]] || fail "A temporary install path already exists; please retry."

say "Downloading the public repository..."
git clone --depth 1 "$REPO" "$WORK_DIR/repo"
[[ -f "$WORK_DIR/repo/app/main.py" && -f "$WORK_DIR/repo/requirements.txt" ]] || fail "Repository is missing required application files."

mkdir -m 700 -- "$STAGE_DIR"
cp -a "$WORK_DIR/repo/app/." "$STAGE_DIR/"
cp -- "$WORK_DIR/repo/requirements.txt" "$STAGE_DIR/requirements.txt"

say "Preparing the isolated Python environment..."
python3 -m venv "$STAGE_DIR/.venv"
"$STAGE_DIR/.venv/bin/python" -m pip install --upgrade pip
"$STAGE_DIR/.venv/bin/python" -m pip install -r "$STAGE_DIR/requirements.txt"

# Swap only this application's dedicated directory. Keep a rollback copy until
# the new installation is in place; user configuration is stored elsewhere.
if [[ -d "$APP_DIR" ]]; then mv -- "$APP_DIR" "$BACKUP_DIR"; fi
if ! mv -- "$STAGE_DIR" "$APP_DIR"; then
  [[ ! -d "$BACKUP_DIR" ]] || mv -- "$BACKUP_DIR" "$APP_DIR"
  fail "Could not activate the new installation; the previous version was restored."
fi
STAGE_DIR=""
SWAPPED=1

cat > "$BIN_DIR/$APP_NAME" <<'LAUNCH'
#!/usr/bin/env bash
exec "$HOME/.local/opt/ak680-controller/.venv/bin/python" "$HOME/.local/opt/ak680-controller/main.py" "$@"
LAUNCH
chmod 755 "$BIN_DIR/$APP_NAME"

cat > "$DESKTOP_DIR/$APP_NAME.desktop" <<DESKTOP
[Desktop Entry]
Name=AJAZZ AK680 Controller
Comment=Linux companion for the AJAZZ AK680 MAX
Exec=$BIN_DIR/$APP_NAME
Icon=input-keyboard
Terminal=false
Type=Application
Categories=Utility;Settings;HardwareSettings;
DESKTOP
chmod 644 "$DESKTOP_DIR/$APP_NAME.desktop"

say "Installation complete."
printf 'Launch from the app menu or run: %s\n' "$BIN_DIR/$APP_NAME"
printf 'Your settings directory is preserved: %s\n' "$CONFIG_DIR"
