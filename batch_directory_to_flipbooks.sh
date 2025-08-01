#!/bin/zsh
# Batch script to run directory_to_flipbooks.py for every Slack channel directory with a 'files' subdirectory
# This is used to create flipbooks for OMATA Slack channels

# List of CMYK flipbook backgrounds to cycle through
cmyk_backgrounds=('61,53,42,14' '0,85,85,0' '22,0,93,0' '58,48,53,18')

# Output directory
output_dir="/Users/julian/Dropbox (Personal)/Projects By Year/@2025/OMATA Process Diary/OMATA-SlackBooks/slack-channel-cards/"

# Find all directories in /Users/julian/Code/SlackExporterForOmata/ that contain a 'files' subdirectory
channel_dirs=(/Users/julian/Code/SlackExporterForOmata/*/files)

# Counter for cycling backgrounds
bg_count=${#cmyk_backgrounds[@]}
idx=0

for files_dir in $channel_dirs; do
    # Get parent channel directory
    channel_dir=$(dirname $files_dir)
    # Cycle through backgrounds
    cmyk_bg=${cmyk_backgrounds[$((idx % bg_count))]}
    echo "Processing $files_dir with cmyk-flipbook-background $cmyk_bg"
    python3 ./directory_to_flipbooks.py "$files_dir" \
        --page-size A5 \
        --page-orientation portrait \
        --video-fps 1 \
        --cmyk-mode \
        --cmyk-flipbook-background "$cmyk_bg" \
        --output-dir "$output_dir"
    idx=$((idx + 1))
done
