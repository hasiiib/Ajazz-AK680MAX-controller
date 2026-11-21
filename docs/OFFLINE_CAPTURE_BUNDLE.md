# Offline read-only configuration bundle

The Configuration (read-only) tab can import a JSON bundle assembled from manually supplied response captures. Import is offline: it does not open HID, send commands, retry, save captures, or modify the keyboard. The target fields are **self-declared metadata**, not proof that the data came from board 2255 or stock firmware.

## Format

The bundle format identifier is `ak680-read-only-capture-bundle-v1`. The root object must contain exactly:

- `format`: the format identifier above.
- `target`: exactly `{"vid_pid":"3151:502D","board_id":2255}`.
- `active_profile_reply`: hex text for one 64-byte payload or 65-byte response with a leading zero report-ID.
- `keymap_replies`: non-empty array of objects `{"sublayer":0,"page":0,"raw_hex":"..."}`.
- `magnetic_replies`: non-empty array of objects `{"subop":0,"page":0,"raw_hex":"..."}`.

Every page is raw hexadecimal text (spaces between bytes are allowed), and must be 64 bytes or 65 bytes with a leading zero report-ID. Each listed keymap sublayer requires all eight keymap pages, numbered 0–7. Each listed magnetic sub-operation requires all of its pages: sub-operations 0, 1, 2, 3, 4, and 6 have four pages; 5, 7, and 9 have two; 10 has eight. The bundle may include only a subset of layers or magnetic sub-operations, but every included dimension must be complete. Duplicate page entries, unknown fields, mismatched target metadata, invalid lengths, or incomplete page sets are rejected.

The importer is limited to 256 KiB. It rejects unknown fields (including serial-number fields), validates the active-profile response, and delegates keymap and magnetic page parsing/assembly to the existing strict validators. It displays raw entries and values only; it does not assign key meanings or magnetic units.

## Import

1. Open the **Configuration (read-only)** tab.
2. Select **Import offline capture bundle…**.
3. Choose a JSON file in the format above.

If validation fails, the current displayed snapshot is retained. If it succeeds, the new snapshot is shown with an explicit warning that device source and firmware provenance have not been verified.

The bundle can be created manually from reviewed one-shot capture output. Do not include the keyboard's unique serial number, USB device path, unrelated logs, or firmware claims. This format is not a hardware-validation substitute and does not authorize any device command or persistent setting write.
