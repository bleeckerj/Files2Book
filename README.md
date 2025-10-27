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
  Where `/SlackExporterOutput` is the root directory by which the elements in `file-list` are relatively specified.

  e.g. here is one element in the `downloaded_files.json`

  ```
    {
    "filepath": "channel/files/1487105611/A_File_Name",
    "raw_ts": "1487105611",
    "actual_ts": "1487105611.000000",
    "permalink": "https://your.slack.com/docs/T08B657GW/F04AB5GC60J",
    "permalink_public": null
    }
```

Here's another command that just reads from a directory:

```
python create_file_cards.py \
  --input-dir "/Volumes/RabbitOne/images/autotrader_1089358474426712224/images/" \
  --border-color "161 216 26" \
  --border-inch-width 0 \
  --output-dir "/Volumes/RabbitOne/images/autotrader_1089358474426712224/images_output" \
  --max-depth 3 \
  --cmyk-mode \
  --page-size DIGEST \
  --pdf-output-name "your_output.pdf" \
  --cards-per-chunk 500 \
  --delete-cards-after-pdf
```

Recursively walks down a directory hierarchy ingesting everything in its path and turning those every things into an preview card. It chunks these in quantities of 500, so you'll get PDFs with 500 pages up to the total accounting of all the files that can be handled. (Actually, even files that cannot be handled will be represented in some fashion, all except "." files which are always ignored no matter what.)

You'll get them as `DIGEST` sized (5.25"x8.25"), CMYK (natch), basically no border and they should be named `autotrader_output`-ish with some indexical reference, all in their own `chunk_xxx` folder, underneath the specified `output-dir`

All of the card files will be deleted (presumably to save disk space as they are typically quite large TIFFs), leaving only 1 or more PDFs.

## Supported Page Sizing

### Various standard book sizes (standard units - inches)
- 'A5': (5.83, 8.27)                  
- 'A5_FULLBLEED': (6.08, 8.52),
- 'A4': (8.27, 11.69),
- 'A3': (11.69, 16.54),
- 'A2': (16.54, 23.39),
- 'A1': (23.39, 33.11),
- 'A0': (33.11, 46.81),
- 'TRADE_LARGE': (7, 9),
- 'LETTER': (8.5, 11),
- 'LEGAL': (8.5, 14),
- 'TABLOID': (11, 17),
- 'DIGEST': (5.5, 8.5),
- 'DIGEST_FULLBLEED': (5.75, 8.75),
- 'POCKETBOOK': (4.25, 6.87),
- 'POCKETBOOK_FULLBLEED': (4.5, 7.12),

### Playing card sizes (in inches, rounded to 2 decimals)
- 'POKER': (2.48, 3.46),        # 63x88mm
- 'BRIDGE': (2.24, 3.46),       # 57x88mm
- 'MINI': (1.73, 2.68),         # 44x68mm
- 'LARGE_TAROT': (2.76, 4.72),  # 70x120mm
- 'SMALL_TAROT': (2.76, 4.25),  # 70x108mm
- 'LARGE_SQUARE': (2.76, 2.76), # 70x70mm
- 'SMALL_SQUARE': (2.48, 2.48), # 63x63mm

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

### Environment Variables

For GPS data file support (`.fit` and `.gpx` files), you'll need a Mapbox access token. Create a `.env` file in the project root:

```bash
MAPBOX_ACCESS_TOKEN=your_mapbox_token_here
```

You can obtain a Mapbox token from https://account.mapbox.com/access-tokens/

### Configuration

Font paths and other settings can be customized in `config.json`. See the default configuration file for available options.


## Some related utilities

Some of these may be somewhat deprectated as they were integrated into `create_file_cards.py` possibly

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
    --page-size A5_FULLBLEED \
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

## Movie File Preview Logic

For movie files (`.mp4`, `.mov`, `.avi`, `.mkv`), the preview shows frames, the number of which are based on the command line parameter `--max-video-frames` which is not an absolute determinant of the number of frames shown but more a hint as the algorithm to lay the frames out really wants to fill the available space in a complete grid with no blank holes and is somewhat imperfect in doing that, but usually is close enough (for jazz).  
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


## Supportive utilities

[generate-filelist-for-files2books](https://github.com/bleeckerj/generate-filelist-for-files2books)

[SlackExporter](https://github.com/bleeckerj/SlackExporter)

[DownloadDiscordImages](https://github.com/bleeckerj/download-discord-images)



## License
Creative Commons Attribution-NonCommercial (CC BY-NC)

This project is licensed under the Creative Commons Attribution-NonCommercial (CC BY-NC) license. You are free to use, share, and adapt the software, provided you give appropriate credit and do not use it for commercial purposes. For more details, see https://creativecommons.org/licenses/by-nc/4.0/
