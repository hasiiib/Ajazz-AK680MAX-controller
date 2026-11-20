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

    def test_installer_stages_standalone_analog_probe(self):
        script = INSTALLER.read_text(encoding="utf-8")
        self.assertIn('"$WORK_DIR/repo/capture_analog_stream.py"', script)
        self.assertIn('cp -- "$WORK_DIR/repo/capture_analog_stream.py" "$STAGE_DIR/capture_analog_stream.py"', script)

    def test_installer_uses_staging_and_rollback_before_activation(self):
        script = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("STAGE_DIR=", script)
        self.assertIn("BACKUP_DIR=", script)
        self.assertIn('mv -- "$APP_DIR" "$BACKUP_DIR"', script)
        self.assertIn('mv -- "$STAGE_DIR" "$APP_DIR"', script)
        self.assertIn("the previous version was restored", script)

    def test_installer_restores_previous_app_if_post_swap_activation_fails(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash is not available")

        import os
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            app_dir = home / ".local" / "opt" / "ak680-controller"
            launcher_dir = home / ".local" / "bin"
            desktop_dir = home / ".local" / "share" / "applications"
            app_dir.mkdir(parents=True)
            launcher_dir.mkdir(parents=True)
            desktop_dir.mkdir(parents=True)
            (app_dir / "previous.marker").write_text("previous-version", encoding="utf-8")
            (launcher_dir / "ak680-controller").write_text("old-launcher", encoding="utf-8")
            (desktop_dir / "ak680-controller.desktop").write_text("old-desktop", encoding="utf-8")

            fake_git = fake_bin / "git"
            fake_git.write_text(
                "#!/bin/sh\n"
                "[ \"$1\" = clone ] || exit 2\n"
                "target=\"$4\"\n"
                "mkdir -p \"$target/app\"\n"
                "printf 'pass\\n' > \"$target/app/main.py\"\n"
                ": > \"$target/requirements.txt\"\n"
                "printf \\\"probe\\\\n\\\" > \\\"$target/capture_analog_stream.py\\\"\n",
                encoding="utf-8",
            )
            fake_python = fake_bin / "python3"
            fake_python.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = -m ] && [ \"$2\" = venv ] && [ \"$3\" = --help ]; then exit 0; fi\n"
                "if [ \"$1\" = -m ] && [ \"$2\" = venv ]; then\n"
                "  mkdir -p \"$3/bin\"\n"
                "  printf '#!/bin/sh\\nexit 0\\n' > \"$3/bin/python\"\n"
                "  chmod 755 \"$3/bin/python\"\n"
                "  exit 0\n"
                "fi\n"
                "exit 2\n",
                encoding="utf-8",
            )
            fake_mv = fake_bin / "mv"
            fake_mv.write_text(
                "#!/bin/sh\n"
                "for arg in \"$@\"; do\n"
                "  case \"$arg\" in\n"
                "    */.ak680-controller.desktop-*)\n"
                "      if [ \"${FAIL_DESKTOP_MOVE:-0}\" = 1 ]; then exit 42; fi\n"
                "      ;;\n"
                "  esac\n"
                "done\n"
                "exec /bin/mv \"$@\"\n",
                encoding="utf-8",
            )
            for path in (fake_git, fake_python, fake_mv):
                path.chmod(0o755)

            env = os.environ.copy()
            env.update({
                "HOME": str(home),
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "FAIL_DESKTOP_MOVE": "1",
            })
            result = subprocess.run(
                [bash, str(INSTALLER)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(
                (app_dir / "previous.marker").read_text(encoding="utf-8"),
                "previous-version",
            )
            self.assertFalse((app_dir / "app" / "main.py").exists())
            self.assertEqual(
                (desktop_dir / "ak680-controller.desktop").read_text(encoding="utf-8"),
                "old-desktop",
            )
            self.assertFalse(list((home / ".local" / "opt").glob(".ak680-controller-backup-*")))
            self.assertFalse(list((home / ".local" / "opt").glob(".ak680-controller-staging-*")))

    def test_installer_never_executes_sudo_or_broad_permission_changes(self):
        script = INSTALLER.read_text(encoding="utf-8")
        executable_sudo = re.compile(r"^\s*sudo(?:\s|$)", re.MULTILINE)
        self.assertIsNone(executable_sudo.search(script))
        self.assertNotRegex(script, r"chmod\s+(?:-R\s+)?777")
        self.assertNotIn("/usr/local/bin", script)
        self.assertNotIn("/usr/lib", script)

    def test_all_application_modules_compile_without_importing_hardware_dependencies(self):
        for source_path in sorted((ROOT / "app").glob("*.py")):
            with self.subTest(module=source_path.name):
                source = source_path.read_text(encoding="utf-8")
                compile(source, str(source_path), "exec")

    def test_udev_access_is_scoped_to_target_usb_identity_and_control_interface(self):
        rules = UDEV_RULES.read_text(encoding="utf-8")
        self.assertIn('ATTR{idVendor}=="3151"', rules)
        self.assertIn('ATTR{idProduct}=="502d"', rules)
        self.assertIn('ENV{ID_USB_INTERFACE_NUM}=="02"', rules)
        self.assertNotRegex(rules, r'ATTR\{idVendor\}=="\*"')
        self.assertNotRegex(rules, r'KERNEL=="hidraw\*"[^\n]*MODE=')


if __name__ == "__main__":
    unittest.main()
