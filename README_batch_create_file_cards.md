# batch_create_file_cards.js

## Description

This Node.js script automates the creation of file cards for every channel directory (with a `files` subdirectory) under a specified root directory. It is designed for batch processing Slack exports or other bulk file sets using the Python script `create_file_cards.py`.

## Usage

```bash
node batch_create_file_cards.js --page-size LARGE_TAROT --root-dir ../SlackExporterForOmata
```
- `--page-size`: Card size (default: LARGE_TAROT)
- `--root-dir`: Root directory containing channel subdirectories (default: ../SlackExporterForOmata)

Each channel directory must contain a `files` subdirectory. The script will run `create_file_cards.py` for each channel, saving output in a directory named `<channel>_file_cards`.

## Requirements
- Node.js
- Python 3
- Required Python packages for `create_file_cards.py` (see its README)
- Node.js package: `minimist` (install with `npm install minimist`)

## Example

If your Slack export is in `../SlackExporterForOmata`, run:
```bash
node batch_create_file_cards.js --root-dir ../SlackExporterForOmata
```

This will process all channels and generate card images for each.

## Notes
- Errors for individual channels are logged but do not stop the batch process.
- Output directories are created per channel.
