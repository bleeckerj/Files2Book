# Files2Book

This is a collection of utilities that were cobbled together in order to support a project where I wanted to archive all of the Slack channels for https://omata.com into a series of books, one book per channel.

## Why?

Well, I ran the company largely alone for 8 years before (happily and profitably) selling the company — and I wanted to memorialize the work and if you know me you know I love the weight of a book and what that weight (can possibly but not always in fact maybe less often) represents. The idea of cooking out physical tangible books from Slack channels, social media exhaust nozzles, folder hierachires, my ‘week notes’ — all things that otherwise would get lost either materially or from memory..well, that's a very ‘Julian’ thing to do.

So, the utility value here is that, to me.

## Eh? What?

There's a 30TB RAID drive array somewhere that contains the bulk of the projects and work I've done over — hah! — nearly 30 years. I gradually shove data from old (and retired) laptops and such, etcetera. But I can't see that stuff, even if I could look at the physical box of RAID arrayed drives and presumably some blinking lights.

How do you ‘scrapbook’ data?

That's the question I guess I was working through.

If my nephews came to the Laboratory and asked, as they have, ‘Yo, unc. 'Sup with all that weird stuff you do?', what am I going to do? Sure, I can tell them stories to the degree I recall things. But suppose I could open a book and start browsing through stuff and recalling stories the way we used to browse through those 3-ring binder photo albums that kept actual wet chemistry photographs?

## Okay. Enough already. What's here?

These convert directories containing PDFs, images, PPTX, and video files into organized print preview cards with optional grid layouts with optional flipbook generation of `movie` file types, although the value of that is more ludic than anything else as `movie` file types will be made into a grid of still frames.

This set of utilities builds on [SlackExporter](https://github.com/bleeckerj/SlackExporter), which is a generalizable exporter of Slack channels. The output of that is a clobber of JSON files and file-files from the channels (files that were in message payloads).

### Why Slack?

Well, that's where I started without knowing where I'd end up. By that I mean, I was somewhat obsessed with making a book from all the Slack messages and files shared therein because OMATA happened a fair bit in Slack (distributed manufacturing and R&D team, etcetera).

[SlackExporter](https://github.com/bleeckerj/SlackExporter) generates a conditioned directory hierarchy for every chanel. File2Card was created to handle the `files` directory that this creates, allowing you to create a PDF document containing representations (`previews`) of many different file types one might encounter that has been shared as message payload.

(I've also created other exporters from various nozzles, endpoints, and ingestion flanges like Midjourney and Instagram that will cook out useful metadata and content — that one can then point `create_file_cards.py` at in various ways, including consuming a properly structured JSON file or just point it at a file hierarchy, and it'll make PDFs suitable for printing.)

For me, that means things like PPTX, PNG, JPG, HEIC/HEIF, MOV, MP4, TXT, ZIP, RAR, PDF and so forth. These file types are converted into some kind of generally useful visual preview, although some are jsut represented as hex dumps, which is only useful aas an index and indicator that, you know — there was this file here, and here is what it is called, and here is where it was shared and, through much more effort, here is who shared it (as it should be referred to in the potentially quite extensive message transcripts.)

The utility of these books? 

Well, I wrote more about that here: 


## Features

- Convert files and such into individual "info" previews — the idiom I use here is `cards`
- Handles a variety of canonical and typical filetypes - images of various formats, video files (making grids of a selection of frames across the entire video, weighted towards the central 80% or so, if memory serves)
- Generate flipbooks from video files, optionally. An older feature.
- Support for various page sizes (A4, A5, Letter, Digest, Pocketbook, etc.)
- Customizable margins and border colors (cause the edges of books deserve some panache)
- Option to include each individual video frame  (`--include-video-frames`) as their own page, which is a bit insane, but might have value in some weird context.
- PDF output support, obvs.
- CMYK color mode support with customizable CMYK values. Perfect for physical printing, which is what this is all about.
 - Optional per-frame video cards in addition to overview grids
 - Cleanup flag to remove generated images after PDF assembly (`--delete-cards-after-pdf`)
 - Exclude the file path to the file with `--exclude-file-path`

## Usage Note

See the individual utilities, but the main useful one I've found is `create_file_cards.py` The other ones were created leading up to this one canonical one, I think.

## Run Examples 

Each little utility has its own configuration, and each has its own README for specifity.

 The main program here is [create_file_cards.py](README_create_file_cards.md) so I'll just refer to it specifically, while also suggesting you may find some of the more nuanced utilities more what you're looking for.

```
 python3 ./create_file_cards.py --page-size "DIGEST" --input-dir "./Chapters/InDesign/CURRENT/04052021/MakingOfOMATA_8x10_V1_01122021 Folder/Links/" --cmyk --output-dir "/Users/julian/Dropbox (Personal)/Projects By Year/@2025/Making Of Book Images Cards/V1/" --max-depth 1 --exclude-file-path --pdf-output-name MakingOfOMATA_V1_ImageBook.pdf
 ```

```
python create_file_cards.py \
  --page-size "5.75x8.75" \
  --slack-data-root "/SlackExporterForOmata/omata-brand/" \
  --file-list "/SlackExporterForOmata/omata-brand/downloaded_files.json" \
  --output-dir "/SlackExporterForOmata/slack-channels-file-cards/omata-brand_file_cards_output" \
  --cmyk-mode \
  --max-depth 3 \
  --border-color "161 216 26" \
  --border-inch-width 0.2 \
  --delete-cards-after-pdf \
  --cards-per-chunk 500 \
  --input-dir "/SlackExporterForOmata/"
  ```
  Where `/SlackExporterForOmata` is the root directory by which the elements in `file-list` are relatively specified.

  e.g. here is one element in the `downloaded_files.json`

  ```
    {
    "filepath": "omata-app/files/1487105611/Calibartion_Screens_based_on_Dir__2A",
    "raw_ts": "1487105611",
    "actual_ts": "1487105611.000000",
    "permalink": "https://omata.slack.com/docs/T08B657GW/F04AB5GC60J",
    "permalink_public": null
    }
```

Here's another command that just reads from a directory:

```
python create_file_cards.py \
  --input-dir "/Volumes/Crucial X10/MidjourneyImages/images/autotrader_1089358474426712224/images/" \
  --border-color "161 216 26" \
  --border-inch-width 0 \
  --output-dir "/Volumes/Crucial X10/MidjourneyImages/autotrader_output" \
  --max-depth 3 \
  --cmyk-mode \
  --page-size DIGEST \
  --pdf-output-name "autotrader_output.pdf" \
  --cards-per-chunk 500 \
  --delete-cards-after-pdf
```

Recursively walks down a directory hierarchy ingesting everything in its path and turning those every things into an preview card. It chunks these in quantities of 500, so you'll get PDFs with 500 pages up to the total accounting of all the files that can be handled. (Actually, even files that cannot be handled will be represented in some fashion, all except "." files which are always ignored no matter what.)

You'll get them as `DIGEST` sized (5.25"x8.25"), CMYK (natch), basically no border and they should be named `autotrader_output`-ish with some indexical reference, all in their own `chunk_xxx` folder, underneath the specified `output-dir`

All of the card files will be deleted (presumably to save disk space as they are typically quite large TIFFs), leaving only 1 or more PDFs.

## Requirements

Obvs, create a Python virtual environment to save any headaches down the road.

Then do the usual incantations:

```bash
source .venv/bin/activate
pip install -r requirements
```

Note: You'll also need `poppler` installed for PDF processing, as the library pdf2image requires it:
- Mac: `brew install poppler`

As I've only run this on macOS, I cannot say how to install Poppler on other platforms, but cf: https://poppler.freedesktop.org/ but Homebrew should support Ubuntu, for example - I'll probably try that.


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


## License
Creative Commons Attribution-NonCommercial (CC BY-NC)

This project is licensed under the Creative Commons Attribution-NonCommercial (CC BY-NC) license. You are free to use, share, and adapt the software, provided you give appropriate credit and do not use it for commercial purposes. For more details, see https://creativecommons.org/licenses/by-nc/4.0/
