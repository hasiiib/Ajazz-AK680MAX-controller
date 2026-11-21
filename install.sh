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
REQUIRED_APP_FILES=(
  active_profile.py
  ak680_max_2255_layout.json
  analog_stream.py
  capture_active_profile.py
  capture_keymap_page.py
  capture_magnetic_page.py
  device_state.py
  diagnostics.py
  hardware_verification.py
  keyboard_layout.py
  keymap.py
  keymap_semantics.py
  keymap_write.py
  lighting.py
  live_configuration.py
  macros.py
  magnetic_settings.py
  magnetic_write.py
  main.py
  offline_snapshot_import.py
  protocol.py
  read_only_snapshot.py
  snapshot_panel.py
  snapshot_view.py
)

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
[[ -f "$WORK_DIR/repo/requirements.txt" && -f "$WORK_DIR/repo/capture_analog_stream.py" ]] || fail "Repository is missing required requirements or analog probe files."
for module in "${REQUIRED_APP_FILES[@]}"; do
  [[ -s "$WORK_DIR/repo/app/$module" ]] || fail "Repository is missing required application module: $module"
done

mkdir -m 700 -- "$STAGE_DIR"
cp -a "$WORK_DIR/repo/app/." "$STAGE_DIR/"
for module in "${REQUIRED_APP_FILES[@]}"; do
  [[ -s "$STAGE_DIR/$module" ]] || fail "Application module staging failed: $module"
done
cp -- "$WORK_DIR/repo/requirements.txt" "$STAGE_DIR/requirements.txt"
# Stage the standalone opt-in probe alongside the installed app modules.
cp -- "$WORK_DIR/repo/capture_analog_stream.py" "$STAGE_DIR/capture_analog_stream.py"
[[ -s "$STAGE_DIR/capture_analog_stream.py" ]] || fail "Analog probe staging failed."

say "Preparing the isolated Python environment..."
python3 -m venv "$STAGE_DIR/.venv"
"$STAGE_DIR/.venv/bin/python" -m pip install --upgrade pip
"$STAGE_DIR/.venv/bin/python" -m pip install -r "$STAGE_DIR/requirements.txt"

# Prepare launcher metadata before touching the active installation. Writing
# temporary files first keeps existing launchers intact if generation fails.
LAUNCHER_TMP="$BIN_DIR/.$APP_NAME-launcher-$BASHPID"
DESKTOP_TMP="$DESKTOP_DIR/.$APP_NAME.desktop-$BASHPID"
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
[[ -s "$APP_DIR/capture_analog_stream.py" ]] || fail "Installed analog probe is missing; the previous version will be restored."
for module in "${REQUIRED_APP_FILES[@]}"; do
  [[ -s "$APP_DIR/$module" ]] || fail "Installed application module is missing: $module; the previous version will be restored."
done

mv -- "$LAUNCHER_TMP" "$BIN_DIR/$APP_NAME"
LAUNCHER_TMP=""
mv -- "$DESKTOP_TMP" "$DESKTOP_DIR/$APP_NAME.desktop"
DESKTOP_TMP=""

say "Installation complete."
printf 'Launch from the app menu or run: %s\n' "$BIN_DIR/$APP_NAME"
printf 'Your settings directory is preserved: %s\n' "$CONFIG_DIR"
