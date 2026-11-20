import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"
UDEV_RULES = ROOT / "udev" / "70-ak680-controller.rules"


class InstallerSafetyTests(unittest.TestCase):
    def test_installer_has_valid_bash_syntax(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash is not available")
        result = subprocess.run(
            [bash, "-n", str(INSTALLER)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_installer_uses_staging_and_rollback_before_activation(self):
        script = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("STAGE_DIR=", script)
        self.assertIn("BACKUP_DIR=", script)
        self.assertIn('mv -- "$APP_DIR" "$BACKUP_DIR"', script)
        self.assertIn('mv -- "$STAGE_DIR" "$APP_DIR"', script)
        self.assertIn("the previous version was restored", script)

    def test_installer_never_executes_sudo_or_broad_permission_changes(self):
        script = INSTALLER.read_text(encoding="utf-8")
        executable_sudo = re.compile(r"^\s*sudo(?:\s|$)", re.MULTILINE)
        self.assertIsNone(executable_sudo.search(script))
        self.assertNotRegex(script, r"chmod\s+(?:-R\s+)?777")
        self.assertNotIn("/usr/local/bin", script)
        self.assertNotIn("/usr/lib", script)

    def test_udev_access_is_scoped_to_target_usb_identity_and_control_interface(self):
        rules = UDEV_RULES.read_text(encoding="utf-8")
        self.assertIn('ATTR{idVendor}=="3151"', rules)
        self.assertIn('ATTR{idProduct}=="502d"', rules)
        self.assertIn('ENV{ID_USB_INTERFACE_NUM}=="02"', rules)
        self.assertNotRegex(rules, r'ATTR\{idVendor\}=="\*"')
        self.assertNotRegex(rules, r'KERNEL=="hidraw\*"[^\n]*MODE=')


if __name__ == "__main__":
    unittest.main()
