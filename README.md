# Files2Books and Slack2Books

This is a collection of utilities that were cobbled together in order to support a project where I wanted to archive all of the Slack channels for https://omata.com into a series of books, one book per channel.

These onvert directories containing PDFs, images, PPTX, and video files into organized print preview cards with optional grid layouts with optional flipbook generation of `movie` file types, although the value of that is more ludic than anything else as `movie` file types will be made into a grid of still frames.

This set of utilities builds on [SlackExporterForOmata](https://github.com/bleeckerj/SlackExporterForOmata), which is a generalizable exporter of Slack channels. The output of that is a clobber of JSON files and file-files from the channels (files that were in message payloads).

[SlackExporterForOmata](https://github.com/bleeckerj/SlackExporterForOmata) generates a conditioned directory hierarchy for every chanel. File2Card was created to handle the `files` directory that this creates, allowing you to create a PDF document containing representations (`previews`) of many different file types one might encounter that has been shared as message payload.

For me, that means things like PPTX, PNG, JPG, HEIC/HEIF, MOV, MP4, TXT, ZIP, RAR, PDF and so forth. These file types are converted into some kind of generally useful visual preview, although some are jsut represented as hex dumps, which is only useful aas an index and indicator that, you know — there was this file here, and here is what it is called, and here is where it was shared and, through much more effort, here is who shared it (as it should be referred to in the potentially quite extensive message transcripts.)

The utility of these books? 

Well, I wrote more about that here: 


## Features

- Convert PDFs and images into grid layouts
- Generate flipbooks from video files
- Support for various page sizes (A4, A5, Letter, Digest, Pocketbook, etc.)
- Configurable grid layouts
- Customizable margins, gaps, and borders
- Option to exclude video stills from main grid pages
- PDF output support
- CMYK color mode support with customizable CMYK values
 - Optional per-frame video cards (`--include-video-frames`) in addition to overview grids
 - Cleanup flag to remove generated images after PDF assembly (`--delete-cards-after-pdf`)

## Usage Note

These utilities has been used to create the shelf books of the Slack channels for OMATA. The extraction of all content from those Slack channels is handled by the separate repository [SlackExporterForOmata](https://github.com/bleeckerj/SlackExporterForOmata).

The steps are to first use SlackExporterForOmata to extract all the messages and files and everything from the channels. The messages appear as gigantic structured data JSON files and the data files that have been shared in the channel appear in a sidecar directory called, you know ``“files”``.

Run `batch_create_file_cards.js` will create “cards” representing the files that have been shared in all of the Slack channels that were digested by `SlackExporterForOmata` formatted and crap. (You can also try running with LARGE_TAROT if you feel like someday printing out actually cards.)

```
node batch_create_file_cards.js --page-size A5 --root-dir ../SlackExporterForOmata --output-dir '/Users/julian/Dropbox (Personal)/Projects By Year/@2025/OMATA Process Diary/OMATA-SlackBooks/file-cards/'
```

---

Run 

```
python3 ./directory_to_flipbooks.py /Users/julian/Code/SlackExporterForOmata/id-explorations/files/ --page-size A5 --p
age-orientation portrait --video-fps 1 --cmyk-mode --cmyk-flipbook-background '61,53
,42,14' --output-dir '/Users/julian/Dropbox (Personal)/Projects By Year/@2025/OMATA Process Diary/OMATA-SlackBooks/slack-channel-cards/'
```

will output in a subdirectory of `--output-dir` a bunch of folders of all the video files found from that Slack channel's shared files turned into 'flipbook' style pages (or cards) and a combined PDF for each, at the `--video-fps` specified

YOu can use `batch_directory_to_flipbooks.sh` to just do this for all of the channels, quite possibly.

Then running `process_all_slack_dirs.py` (here from this repo) will churn on all of that and make pages and combined PDFs for each Slack channel suitable for printing books and putting them on your shelf. (It will not create the covers and spine..you have to do that by hand at the moment.)

Oh, the `SlackExporterForOmata` will also create an `avatar` directory containing tiny avatar icons, and a few other json files like `channels.json` and `users.json`. `user.json is used here to create tables and indices of various sorts.

### Create the cards at LARGE_TAROT size

`python3 generate_flipbook_pages.py --page-size LARGE_TAROT --input-dir ../SlackExporterForOmata/omata-backoffice/files --output-dir omata-backoffice_file_cards --cmyk-mode`

This will go through all the files in the input directory and generate a card that is a kind of preview of the file contents, varying depending on what kind of data the file represents (image, zip, fit, gpx, etc.)

### Combines them into a PDF where each pageis A5

`./combine_images_to_pdf.js --input-dir omata-backoffice_file_cards --cmyk-mode --page-size A5 --dpi 300 --output-file omata-backoffice_file_cards/omata-backoffice_file_cards_combined.pdf`

### New flags in create_file_cards.py

- `--cmyk`: alias for `--cmyk-mode`
- `--include-video-frames`: include individual video frame cards in addition to the overview
- `--delete-cards-after-pdf`: delete `*_card.*` and `*_card_*.*` images after combining into a PDF

This will get you a PDF combining all of the cards, each one embedded on an A5 sized page.

## Requirements

```bash
pip install pillow pdf2image opencv-python numpy
```

Note: You'll also need `poppler` installed for PDF processing:
- Mac: `brew install poppler`

## Usage

Basic usage:
```bash
python3 directory_to_images.py /path/to/input/directory [options]
```

Or:
```bash
python3 process_all_slack_dirs.py
```

This, when pointed appropriately, will create all the stuff.

### Command Line Arguments

Required:
- `input_dir`: Path to directory containing images, PDFs, and/or videos

Optional:
- `--layout`: Choose 'grid' or 'masonry' (default: grid)
- `--page-size`: Page size (e.g., 'A4', 'A5', '8.5x11', 'ANSI A') (default: 8.5x11)
- `--page-orientation`: 'portrait' or 'landscape' (default: portrait)
- `--image-fit-mode`: 'uniform', 'rotate', or 'scale' (default: uniform)
- `--grid-rows`: Number of rows in grid layout
- `--grid-cols`: Number of columns in grid layout
- `--grid`: Shorthand for grid size (e.g., '2x3')
- `--gap`: Gap between images in inches (default: 0.0333)
- `--hairline-width`: Border width in inches (default: 0.0033)
- `--hairline-color`: Border color (default: black)
- `--padding`: Space between image and border in inches (default: 0.0167)
- `--page-margin`: Page margin in inches (default: 0.25)
- `--output-pdf`: Generate a PDF of all pages
- `--output-dir`: Custom output directory
- `--flipbook-mode`: Enable flipbook creation from videos
- `--video-fps`: Frames per second for video extraction (default: 1)
- `--exclude-video-stills`: Exclude video frames from main grid pages
- `--handle-non-visual`: Create information cards for non-visual files (default: true)
- `--no-handle-non-visual`: Skip non-visual files (don't create information cards)
- `--cmyk-mode`: Output images in CMYK color mode instead of RGB
- `--cmyk-background`: CMYK background color as C,M,Y,K values (0-255, comma-separated, defaults to 0,0,0,0 which is white)
- `--cmyk-flipbook-background`: CMYK background color for flipbook blank pages as C,M,Y,K values (0-255, comma-separated, defaults to 22,0,93,0 which is Omata acid green)

### Example Commands

Create a 3x2 grid of images on A5 paper:
```bash
python3 directory_to_images.py /path/to/files/ \
    --layout grid \
    --grid-rows 3 \
    --grid-cols 2 \
    --page-size A5 \
    --page-orientation portrait \
    --image-fit-mode scale \
    --gap 0.125 \
    --hairline-width 0.006 \
    --hairline-color gray \
    --padding 0.125 \
    --page-margin 0.35 \
    --output-pdf
```

Generate flipbooks from videos while excluding video stills from main pages:
```bash
python3 directory_to_images.py /path/to/files/ \
    --layout grid \
    --grid-rows 3 \
    --grid-cols 2 \
    --page-size A5 \
    --flipbook-mode \
    --video-fps 1 \
    --exclude-video-stills \
    --output-pdf
```

Create a grid with CMYK color mode using a specific background color:
```bash
python3 directory_to_images.py /path/to/files/ \
    --layout grid \
    --grid-rows 2 \
    --grid-cols 1 \
    --page-size A5 \
    --cmyk-mode \
    --cmyk-background 0,0,0,0 \
    --output-pdf
```

Create flipbooks with custom background colors for both content pages and blank pages:
```bash
python3 directory_to_images.py /path/to/files/ \
    --layout grid \
    --grid-rows 2 \
    --grid-cols 1 \
    --page-size A5 \
    --flipbook-mode \
    --cmyk-mode \
    --cmyk-background 0,0,0,0 \
    --cmyk-flipbook-background 22,0,93,0 \
    --output-pdf
```

## Batch Processing All Slack Channels

To process all Slack channel directories at once (for example, to generate shelf books for every channel), use the provided `process_all_slack_dirs.py` script. This script will automatically run `directory_to_images.py` for every channel directory (with a `files/` subdirectory) in your exported Slack workspace folder.

### Command Line Arguments for Batch Processing

- `--base-dir`: Path to the base directory containing all Slack export directories (default: "/Users/julian/Code/SlackExporterForOmata")
- `--script-path`: Path to the directory_to_images.py script (default: "/Users/julian/Code/pdf-to-grid-of-images/directory_to_images.py")

### Example Usage

Basic usage with default paths:
```bash
python3 process_all_slack_dirs.py
```

Specifying custom paths:
```bash
python3 process_all_slack_dirs.py \
    --base-dir /path/to/slack/exports \
    --script-path /path/to/directory_to_images.py
```

This will generate output pages and flipbooks for every channel in your Slack export, using the options specified in the script.

## CMYK Color Mode

The tool supports CMYK (Cyan, Magenta, Yellow, Black) color mode for professional printing applications. When CMYK mode is enabled:

- Images are saved as TIFF files instead of PNG for better color space support
- You can specify custom CMYK background values (0-255 for each channel)
- PDF output is optimized for print production

CMYK mode is particularly useful when preparing documents for professional printing services where precise color reproduction is important.

### Background Colors

You can set different CMYK background colors for both regular pages and flipbook blank pages:

- `--cmyk-background`: Sets the background color for all regular content pages
- `--cmyk-flipbook-background`: Sets the background color specifically for blank pages inserted in flipbook mode to ensure all flipbook frames appear on recto (right) pages

Example CMYK values:
- `0,0,0,0`: White
- `0,0,0,100`: Black
- `100,0,0,0`: Cyan
- `0,100,0,0`: Magenta
- `0,0,100,0`: Yellow
- `22,0,93,0`: Omata acid green (default for flipbook blank pages)

Note: When using CMYK mode, the output files will be larger due to the TIFF format.

## Non-Visual Files Support

The tool can now create visual representations for non-visual file types such as code files, data files, spreadsheets, archives, and more. When enabled, it generates information cards for these files that include:

- File name, type, and size
- Creation and modification dates
- File type identification icon
- Content preview (for text-based files)
- MD5 hash for file verification

### Supported Non-Visual File Types

The tool automatically categorizes files into these groups:

- **Code**: `.py`, `.js`, `.html`, `.css`, `.java`, `.c`, `.cpp`, `.h`, `.sh`, `.rb`, `.swift`, `.php`, `.go`
- **Data**: `.json`, `.csv`, `.xml`, `.yaml`, `.yml`, `.toml`, `.ini`
- **Spreadsheets**: `.xlsx`, `.xls`, `.ods`, `.numbers`
- **Documents**: `.doc`, `.docx`, `.txt`, `.md`, `.rtf`, `.odt`, `.pdf`, `.tex`
- **Archives**: `.zip`, `.tar`, `.gz`, `.bz2`, `.rar`, `.7z`
- **Executables**: `.exe`, `.bin`, `.app`, `.sh`, `.bat`, `.dll`, `.so`, `.dylib`
- **Binary**: `.hex`, `.bin`, `.dat`, `.dfu`, `.oci`
- **GPS Data**: `.gpx`, `.fit`, `.tcx`
- **Log Files**: `.log`, `.txt`, `.out`

Any other file types will be rendered with a generic file information card.

### Example Command with Non-Visual File Support

Process all files in a directory, including creating information cards for non-visual files:

```bash
python3 directory_to_images.py /path/to/files/ \
    --layout grid \
    --grid-rows 2 \
    --grid-cols 1 \
    --handle-non-visual \
    --output-pdf
```

To process only visual files (images, PDFs, videos) and skip non-visual files:

```bash
python3 directory_to_images.py /path/to/files/ \
    --layout grid \
    --grid-rows 2 \
    --grid-cols 1 \
    --no-handle-non-visual \
    --output-pdf
```

# PDF to Grid of Images

This tool processes files and creates visual file cards, which can be combined into a single PDF.

## Features

- Generates file info cards from various file types
- Supports both RGB and CMYK color modes
- Displays file metadata, previews, and visual indicators
- Handles special file types like GPS files, archives, and more
- Assembles cards into a single PDF document

## Usage

```bash
python generate_flipbook_pages.py --input-dir ./files --output-dir ./card_output --cmyk-mode --page-size LARGE_TAROT
```

### Options

- `--input-dir`: Directory containing files to create cards for
- `--output-dir`: Directory to save card images (default: file_card_tests)
- `--cmyk-mode`: Generate cards in CMYK mode (for printing)
- `--page-size`: Card size (A4, LETTER, TABLOID, POKER, BRIDGE, etc. or WxH in inches)
- `--pdf-output-name`: Filename to save for the combined PDF

## PDF Assembly

For highest quality PDF assembly, use the Node.js script:

```bash
node combine_images_to_pdf.js -i ./card_output -o combined_cards.pdf --cmyk-mode --sort-order name
```

```bash
combine_images_to_pdf.js --input-dir general_file_cards --cmyk-mode --page-size A5 --dpi 300 --output-file general_file_cards/general_file_cards_combined.pdf
```

## Requirements

- Python 3.7+
- Pillow (PIL Fork)
- Additional requirements in requirements.txt

# file_card_generator README

file_card_generator.py generates visual info cards for files of many types.

Supported preview types:
- Images (PNG, JPG, etc.)
- PDF
- Text/code/data files
- Keynote (.key): Lists contents and shows embedded images in a grid
- DOCX (.docx): Extracts and previews text

Not yet supported:
- PPTX (.pptx): No preview, only metadata

Other features:
- Slack metadata integration
- GPS/Map previews for GPX/FIT
- Archive previews (ZIP, GZ, BZ2)

See the code for details on each preview type.

## Movie File Preview Logic

For movie files (`.mp4`, `.mov`, `.avi`, `.mkv`), the preview shows a grid of 4 frames.  
Frames are selected as follows:
- One random frame from the first 10% of the video
- One random frame from 10%–50%
- One random frame from 50%–90%
- One random frame from the last 10%

Each frame is extracted using OpenCV, converted to a PIL image, and:
- If the preview area is portrait (taller than wide) and the frame is landscape, the frame is rotated 90° to better fill the preview box.
- Each frame is scaled to fit its grid cell before being pasted into the grid.

## Spreadsheet Preview Logic

For spreadsheet files (`.xlsx`, `.xls`):
- The code uses `openpyxl` for `.xlsx` and `xlrd` for `.xls` to read the first sheet.
- It extracts and displays the first few rows and columns as a text preview, formatted as a simple table.

For Apple Numbers files (`.numbers`):
- The file is treated as a ZIP archive.
- The code lists the contents and, if a preview image is found inside, displays it as the preview.

## Image Rotation

For all image previews (including movie frames and PDF/AI pages):
- If the preview card is portrait and the image/frame is landscape, the image/frame is rotated 90° before scaling.
- This ensures the preview makes optimal use of the available space.

## Examples relavant to my work / OMATA

```
 python3 ./create_file_cards.py --page-size "DIGEST" --input-dir "./Chapters/InDesign/CURRENT/04052021/MakingOfOMATA_8x10_V1_01122021 Folder/Links/" --cmyk --output-dir "/Users/julian/Dropbox (Personal)/Projects By Year/@2025/Making Of Book Images Cards/V1/" --max-depth 1 --exclude-file-path --pdf-output-name MakingOfOMATA_V1_ImageBook.pdf
 ```


## License
Creative Commons Attribution-NonCommercial (CC BY-NC)

This project is licensed under the Creative Commons Attribution-NonCommercial (CC BY-NC) license. You are free to use, share, and adapt the software, provided you give appropriate credit and do not use it for commercial purposes. For more details, see https://creativecommons.org/licenses/by-nc/4.0/
