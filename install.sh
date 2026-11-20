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
LAUNCHER_TMP=""
DESKTOP_TMP=""
HAD_APP=0
SWAPPED=0

say() { printf '\n[AK680] %s\n' "$*"; }
fail() { printf '\n[AK680] ERROR: %s\n' "$*" >&2; exit 1; }
cleanup() {
  local status=$?
  if [[ -n "$STAGE_DIR" && -d "$STAGE_DIR" ]]; then rm -rf -- "$STAGE_DIR" || true; fi
  if [[ -n "$LAUNCHER_TMP" && -e "$LAUNCHER_TMP" ]]; then rm -f -- "$LAUNCHER_TMP" || true; fi
  if [[ -n "$DESKTOP_TMP" && -e "$DESKTOP_TMP" ]]; then rm -f -- "$DESKTOP_TMP" || true; fi

  if (( status != 0 )); then
    if (( SWAPPED == 1 )); then
      if [[ -e "$APP_DIR" ]]; then rm -rf -- "$APP_DIR" || true; fi
      if [[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR" ]]; then
        mv -- "$BACKUP_DIR" "$APP_DIR" || true
      elif (( HAD_APP == 0 )); then
        rm -f -- "$BIN_DIR/$APP_NAME" "$DESKTOP_DIR/$APP_NAME.desktop" || true
      fi
    elif [[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR" && ! -e "$APP_DIR" ]]; then
      mv -- "$BACKUP_DIR" "$APP_DIR" || true
    fi
  elif [[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR" ]]; then
    rm -rf -- "$BACKUP_DIR" || true
  fi

  if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then rm -rf -- "$WORK_DIR" || true; fi
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

# Prepare launcher metadata before touching the active installation. Writing
# temporary files first keeps existing launchers intact if generation fails.
LAUNCHER_TMP="${BIN_DIR}/.${APP_NAME}-launcher-$"
DESKTOP_TMP="${DESKTOP_DIR}/.${APP_NAME}.desktop-$"
[[ ! -e "$LAUNCHER_TMP" && ! -e "$DESKTOP_TMP" ]] || fail "A temporary launcher path already exists; please retry."

cat > "$LAUNCHER_TMP" <<'LAUNCH'
#!/usr/bin/env bash
exec "$HOME/.local/opt/ak680-controller/.venv/bin/python" "$HOME/.local/opt/ak680-controller/main.py" "$@"
LAUNCH
chmod 755 "$LAUNCHER_TMP"

cat > "$DESKTOP_TMP" <<DESKTOP
[Desktop Entry]
Name=AJAZZ AK680 Controller
Comment=Linux companion for the AJAZZ AK680 MAX
Exec=$BIN_DIR/$APP_NAME
Icon=input-keyboard
Terminal=false
Type=Application
Categories=Utility;Settings;HardwareSettings;
DESKTOP
chmod 644 "$DESKTOP_TMP"

# Swap only this application's dedicated directory. Any failure after the
# transaction starts restores the previous application; first-install failures
# remove the incomplete app and newly created launchers.
if [[ -d "$APP_DIR" ]]; then
  HAD_APP=1
  mv -- "$APP_DIR" "$BACKUP_DIR"
fi
SWAPPED=1
if ! mv -- "$STAGE_DIR" "$APP_DIR"; then
  fail "Could not activate the new installation; the previous version was restored."
fi
STAGE_DIR=""

mv -- "$LAUNCHER_TMP" "$BIN_DIR/$APP_NAME"
LAUNCHER_TMP=""
mv -- "$DESKTOP_TMP" "$DESKTOP_DIR/$APP_NAME.desktop"
DESKTOP_TMP=""

say "Installation complete."
printf 'Launch from the app menu or run: %s\n' "$BIN_DIR/$APP_NAME"
printf 'Your settings directory is preserved: %s\n' "$CONFIG_DIR"
