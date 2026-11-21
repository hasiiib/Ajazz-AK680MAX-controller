"""Offline profile workspace for validated board-2255 capture bundles.

This module deliberately has no HID access or settings-write transport. A workspace
is a local, editable container of named, validated configuration snapshots.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from offline_snapshot_import import (
    MAX_BUNDLE_BYTES,
    SnapshotImportError,
    import_snapshot_bundle_text,
    export_snapshot_bundle_text,
)
from read_only_snapshot import ReadOnlyConfigurationSnapshot

WORKSPACE_FORMAT = "ak680-profile-workspace-v1"
MAX_WORKSPACE_BYTES = 1024 * 1024
MAX_PROFILES = 4
MAX_PROFILE_NAME = 48


class ProfileWorkspaceError(ValueError):
    """Workspace is malformed or violates workspace limits."""


@dataclass(frozen=True)
class WorkspaceProfile:
    name: str
    snapshot: ReadOnlyConfigurationSnapshot

    def __post_init__(self):
        if not isinstance(self.name, str):
            raise ProfileWorkspaceError("Profile name must be text.")
        name = self.name.strip()
        if not name or len(name) > MAX_PROFILE_NAME:
            raise ProfileWorkspaceError(f"Profile name must be 1–{MAX_PROFILE_NAME} characters.")
        if any(ord(ch) < 32 for ch in name):
            raise ProfileWorkspaceError("Profile name contains control characters.")
        if not isinstance(self.snapshot, ReadOnlyConfigurationSnapshot):
            raise ProfileWorkspaceError("Profile requires a validated configuration snapshot.")
        object.__setattr__(self, "name", name)


@dataclass(frozen=True)
class ProfileWorkspace:
    profiles: tuple[WorkspaceProfile, ...]

    def __post_init__(self):
        if not isinstance(self.profiles, tuple) or not self.profiles:
            raise ProfileWorkspaceError("Workspace must contain at least one profile.")
        if len(self.profiles) > MAX_PROFILES:
            raise ProfileWorkspaceError("Workspace supports at most four profiles.")
        if any(not isinstance(p, WorkspaceProfile) for p in self.profiles):
            raise ProfileWorkspaceError("Workspace entries must be validated WorkspaceProfile objects.")
        names = [p.name.casefold() for p in self.profiles]
        if len(set(names)) != len(names):
            raise ProfileWorkspaceError("Profile names must be unique (case-insensitive).")


def workspace_to_text(workspace: ProfileWorkspace) -> str:
    """Serialize a validated workspace; all snapshots are normalized bundles."""
    if not isinstance(workspace, ProfileWorkspace):
        raise ProfileWorkspaceError("Expected a validated ProfileWorkspace.")
    root = {
        "format": WORKSPACE_FORMAT,
        "profiles": [
            {"name": p.name, "snapshot_bundle": export_snapshot_bundle_text(p.snapshot)}
            for p in workspace.profiles
        ],
    }
    text = json.dumps(root, indent=2, sort_keys=True)
    if len(text.encode("utf-8")) > MAX_WORKSPACE_BYTES:
        raise ProfileWorkspaceError("Workspace exceeds the 1 MiB size limit.")
    return text


def workspace_from_text(text: str) -> ProfileWorkspace:
    """Strictly import workspace text and validate every embedded snapshot."""
    if not isinstance(text, str):
        raise ProfileWorkspaceError("Workspace content must be text.")
    try:
        if len(text.encode("utf-8")) > MAX_WORKSPACE_BYTES:
            raise ProfileWorkspaceError("Workspace exceeds the 1 MiB size limit.")
    except UnicodeEncodeError as exc:
        raise ProfileWorkspaceError("Workspace contains invalid Unicode.") from exc
    try:
        root = json.loads(text)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ProfileWorkspaceError("Workspace is not valid JSON.") from exc
    if not isinstance(root, dict) or set(root) != {"format", "profiles"}:
        raise ProfileWorkspaceError("Workspace root must contain exactly format and profiles.")
    if root["format"] != WORKSPACE_FORMAT:
        raise ProfileWorkspaceError("Unsupported workspace format.")
    items = root["profiles"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_PROFILES:
        raise ProfileWorkspaceError("Workspace must contain between one and four profiles.")
    profiles = []
    for i, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != {"name", "snapshot_bundle"}:
            raise ProfileWorkspaceError(f"Profile entry {i} has an invalid schema.")
        name = item["name"]
        bundle = item["snapshot_bundle"]
        if not isinstance(bundle, str) or len(bundle.encode("utf-8")) > MAX_BUNDLE_BYTES:
            raise ProfileWorkspaceError(f"Profile entry {i} has invalid or oversized snapshot data.")
        try:
            snapshot = import_snapshot_bundle_text(bundle)
        except SnapshotImportError as exc:
            raise ProfileWorkspaceError(f"Profile entry {i} snapshot rejected: {exc}") from exc
        profiles.append(WorkspaceProfile(name, snapshot))
    try:
        return ProfileWorkspace(tuple(profiles))
    except ProfileWorkspaceError:
        raise
