import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from profile_workspace import (
    MAX_PROFILES, ProfileWorkspace, ProfileWorkspaceError, WorkspaceProfile,
    workspace_from_text, workspace_to_text,
)
from offline_snapshot_import import export_snapshot_bundle_text
from read_only_snapshot import build_read_only_snapshot


def make_snapshot(profile=0):
    active = bytearray(64)
    active[0] = 0x84
    active[1] = profile
    keymaps = {}
    for sublayer in range(1):
        for page in range(8):
            raw = bytearray(64)
            raw[0] = 0
            keymaps[(sublayer, page)] = bytes(raw)
    magnetic = {}
    for page in range(4):
        raw = bytearray(64)
        for offset in range(0, 64, 2):
            raw[offset:offset + 2] = (200).to_bytes(2, "little")
        magnetic[(0, page)] = bytes(raw)
    return build_read_only_snapshot(active, keymaps, magnetic, sublayers=(0,), magnetic_subops=(0,))


class ProfileWorkspaceTests(unittest.TestCase):
    def test_round_trip_named_snapshot(self):
        workspace = ProfileWorkspace((WorkspaceProfile("Gaming", make_snapshot()),))
        decoded = workspace_from_text(workspace_to_text(workspace))
        self.assertEqual(decoded.profiles[0].name, "Gaming")
        self.assertEqual(decoded.profiles[0].snapshot.active_profile, 0)

    def test_names_trimmed_and_casefold_unique(self):
        a = WorkspaceProfile("  Work  ", make_snapshot())
        b = WorkspaceProfile("work", make_snapshot())
        with self.assertRaises(ProfileWorkspaceError):
            ProfileWorkspace((a, b))
        self.assertEqual(a.name, "Work")

    def test_rejects_empty_or_too_many_profiles(self):
        with self.assertRaises(ProfileWorkspaceError):
            ProfileWorkspace(())
        with self.assertRaises(ProfileWorkspaceError):
            ProfileWorkspace(tuple(WorkspaceProfile(f"P{i}", make_snapshot()) for i in range(MAX_PROFILES + 1)))

    def test_rejects_invalid_names(self):
        for name in ("", "  ", "x" * 49, "bad\nname", 1):
            with self.subTest(name=name):
                with self.assertRaises(ProfileWorkspaceError):
                    WorkspaceProfile(name, make_snapshot())

    def test_strict_root_and_profile_entry_schema(self):
        for payload in (
            {"format": "bad", "profiles": []},
            {"format": "ak680-profile-workspace-v1", "profiles": [], "extra": 1},
            {"format": "ak680-profile-workspace-v1", "profiles": [{"name": "x"}]},
        ):
            with self.assertRaises(ProfileWorkspaceError):
                workspace_from_text(json.dumps(payload))

    def test_rejects_malformed_json_and_non_text(self):
        for value in ("{", None, 5):
            with self.assertRaises(ProfileWorkspaceError):
                workspace_from_text(value)

    def test_rejects_invalid_embedded_snapshot_bundle(self):
        payload = {"format": "ak680-profile-workspace-v1", "profiles": [
            {"name": "Bad", "snapshot_bundle": "{}"}
        ]}
        with self.assertRaises(ProfileWorkspaceError):
            workspace_from_text(json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
