# Profile Workspace (offline)

The controller now has an offline profile-workspace data layer for holding up to
four named, validated configuration snapshots.

- A profile is a name plus a validated normalized capture bundle.
- Names are trimmed, bounded, control-character-free, and unique without regard
  to case.
- Embedded bundles are validated using the existing strict snapshot importer.
- Workspace JSON is schema-checked and size-limited (1 MiB total).
- This layer does not communicate with the keyboard, switch profiles, or apply
  settings. Hardware writes remain gated on protocol verification, recovery
  design, backup/readback, and explicit user approval.

This is a foundation for the future profile editor UI; it is not a device-side
profile switcher and does not guarantee the saved snapshot is a live capture.
