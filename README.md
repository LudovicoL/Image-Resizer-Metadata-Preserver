# Image Resizer & Metadata Preserver

Batch-convert images to **JPEG**, limit their resolution to **8 megapixels (MP) by default**, and preserve compatible photographic metadata using **Pillow**, **pillow-heif**, and **ExifTool**.

The tool processes images from one directory and writes new JPEG files to a separate output directory. Original files are never modified.

> **Project entry point:** `resize_images.py`  
> This README documents the Python script described in this project. Place `README.md` alongside `resize_images.py` in your repository.

## Features

- **Consistent JPEG output:** Converts supported source images to `.jpg`, regardless of their original format.
- **Maximum resolution:** Downscales images larger than the configured limit (default: **8 MP**), while preserving their aspect ratio.
- **No upscaling:** Images already at or below the limit keep their original pixel dimensions, but are still encoded as JPEG.
- **High-quality resampling:** Uses Pillow's **LANCZOS** filter.
- **Metadata transfer:** Uses ExifTool to copy metadata compatible with JPEG, including common EXIF, GPS, and XMP information when present.
- **Orientation handling:** Applies EXIF orientation to pixels before writing the JPEG, then sets the output orientation tag to normal (`1`).
- **Transparency handling:** Composites transparent inputs onto a **white background** (JPEG does not support transparency).
- **Separate output directory:** Leaves source images untouched and retains each filename's stem, changing only the extension to `.jpg`.
- **Collision safeguards:** Skips output files that already exist and source files that would produce duplicate JPEG names within the same run.
- **Per-file error handling:** Reports failures without stopping the entire batch.
- **Temporary-file workflow:** Writes to a temporary JPEG first, then moves completed output into place.
- **Filesystem timestamps:** Attempts to preserve source file timestamps and permissions where supported.

## Supported input formats

The script recognizes these file extensions:

| Format | Extensions |
| --- | --- |
| JPEG | `.jpg`, `.jpeg` |
| HEIC / HEIF | `.heic`, `.heif` |
| PNG | `.png` |
| TIFF | `.tif`, `.tiff` |
| WebP | `.webp` |
| Bitmap | `.bmp` |

Actual decoding support depends on the installed Pillow and pillow-heif builds. **All successful outputs use the `.jpg` extension.**

## Requirements

- **Python**: Python **3.10 or newer recommended**, with `pip` available. Check the supported Python versions for the specific Pillow and pillow-heif releases you install.
- **Python packages**: `Pillow` and `pillow-heif`.
- **External program**: **ExifTool**, installed separately and available on your system's `PATH` as the `exiftool` command.
- **Memory and disk space**: Enough free RAM to decode very large images, plus space for the output JPEGs.

ExifTool is **not** installed by `pip install pillow pillow-heif`.

### 1. Install Python dependencies

From the project directory:

```bash
python -m pip install --upgrade pip
python -m pip install pillow pillow-heif
```

On some systems, the Python executable is `python3` instead of `python`.

### 2. Install ExifTool

#### macOS (Homebrew)

```bash
brew install exiftool
```

#### Ubuntu / Debian

```bash
sudo apt update
sudo apt install libimage-exiftool-perl
```

#### Windows

1. Download the Windows executable from the [official ExifTool website](https://exiftool.org/).
2. Follow the official Windows installation instructions, including renaming the executable to `exiftool.exe` if required by the downloaded distribution.
3. Place the executable in a directory included in your **PATH** (or add its directory to PATH).
4. Open a **new** PowerShell or Command Prompt window so changes to PATH are picked up.

#### Verify installation

```bash
exiftool -ver
```

The command should print an ExifTool version number. If the shell reports that the command is not recognized or found, check your installation and PATH configuration.

### Optional: Use a virtual environment

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pillow pillow-heif
```

**Windows (PowerShell):**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pillow pillow-heif
```

A virtual environment isolates Python packages; ExifTool must still be installed separately.

## Usage

```bash
python resize_images.py INPUT_DIRECTORY OUTPUT_DIRECTORY [--mp MEGAPIXELS]
```

### Resize to the default 8 MP limit

```bash
python resize_images.py ./originals ./output
```

### Choose a different maximum resolution

For a maximum of 12 MP:

```bash
python resize_images.py ./originals ./output --mp 12
```

### Use directories containing spaces

```bash
python resize_images.py "/path/to/My Photos" "/path/to/Converted Photos"
```

**Windows example:**

```powershell
py resize_images.py "C:\Photos\Originals" "C:\Photos\Output" --mp 8
```

### Command-line arguments

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `input` | Yes | — | Directory containing source images. |
| `output` | Yes | — | Directory where JPEG images will be written. Created if needed. |
| `--mp` | No | `8` | Maximum image resolution in megapixels; must be a finite positive number. |

The current script processes **only files directly inside the input directory**. It does **not** recurse into subdirectories.

## How resizing works

The script compares each image's pixel count with the configured maximum:

```text
megapixels = width × height / 1,000,000
```

- **Above the limit:** The image is downscaled proportionally using LANCZOS.
- **At or below the limit:** Its pixel dimensions are unchanged. It is **still converted/re-encoded to JPEG** and its metadata is transferred.

The result is approximately the requested maximum megapixel count; integer rounding may cause the exact total to be slightly lower.

### Example

| Source file | Original resolution | Output file | Result |
| --- | ---: | --- | --- |
| `IMG_001.HEIC` | 48 MP | `IMG_001.jpg` | Downscaled to approximately 8 MP |
| `IMG_002.png` | 12 MP | `IMG_002.jpg` | Downscaled to approximately 8 MP |
| `IMG_003.jpg` | 5 MP | `IMG_003.jpg` | Original dimensions retained; JPEG re-encoded |
| `IMG_004.tiff` | 200 MP | `IMG_004.jpg` | Downscaled to approximately 8 MP |

Example console output:

```text
Images found: 3
Maximum resolution: 8.0 MP
Output format: JPEG
Metadata preservation: Enabled

[RESIZED] IMG_001.HEIC -> IMG_001.jpg | 48.00 MP -> 8.00 MP (3266x2449) | Metadata transferred
[CONVERTED] IMG_003.jpg -> IMG_003.jpg | 5.00 MP -> 5.00 MP (2500x2000) | Metadata transferred
[SKIPPED] IMG_005.png: Output file already exists.

Processing completed.
Successfully processed: 2
Skipped: 1
Errors: 0
```

*Console values above are illustrative; actual dimensions and output vary by image.*

## Metadata preservation

After generating each JPEG, the script invokes **ExifTool** to transfer tags from the original image into the output JPEG. It attempts to preserve compatible information such as:

- Original capture date/time (for example `DateTimeOriginal`)
- Camera make and model
- Lens and exposure information, ISO, focal length, and aperture
- GPS latitude, longitude, altitude, and related tags
- Compatible EXIF and XMP metadata

The script then sets JPEG orientation to **normal (`1`)**, because the source orientation has already been applied to image pixels. It updates EXIF image width and height fields to the new dimensions.

### Important metadata limitations

**Metadata preservation is best-effort, not byte-for-byte copying.** JPEG, HEIC, TIFF, PNG, and other formats support different metadata structures. Some manufacturer-specific MakerNotes, proprietary fields, auxiliary image data, thumbnails, depth information, or other tags may not be transferable to JPEG. ExifTool may warn about unsupported or non-writable tags.

The script does **not** explicitly embed the source ICC color profile when creating the JPEG with Pillow. Copying metadata afterward is not a guarantee that the original color profile will be preserved or that colors will be managed correctly for every input color space. If accurate color management is critical, extend and validate the workflow before using it for production work.

The script tries to preserve filesystem modification/access timestamps via `shutil.copystat()`. Filesystem **creation/birth time is not guaranteed to be preserved**, and filesystem timestamps are different from the photographic capture date stored in EXIF.

### Inspect metadata

Inspect selected tags in a source image:

```bash
exiftool -time:all -Make -Model -GPS:All ./originals/IMG_001.HEIC
```

Inspect the exported JPEG:

```bash
exiftool -time:all -Make -Model -GPS:All ./output/IMG_001.jpg
```

For a broader comparison, run `exiftool -a -G1 -s` against both files, keeping in mind that format-specific differences are expected.

> **Privacy warning:** GPS coordinates and other metadata may reveal where and when an image was captured. This tool is designed to **preserve** those details, not remove them. Review metadata before uploading exported photographs publicly.

## Output naming and overwrite policy

The output filename uses the source filename **without its original extension**, followed by `.jpg`.

```text
originals/
  holiday.heic
  landscape.png
  portrait.jpeg

output/
  holiday.jpg
  landscape.jpg
  portrait.jpg
```

- **Existing output files are skipped**, not overwritten.
- If two input files would map to the same output name (for example `photo.heic` and `photo.png`), **only the first one in the sorted processing order is eligible**; the other is skipped.
- Filename collision detection within a run is case-insensitive, even on case-sensitive filesystems.
- Input and output directories must be different.

If you need to regenerate a file, remove or move its existing output JPEG first.

## JPEG output settings

By default, output JPEGs are saved using:

| Setting | Value |
| --- | --- |
| Format | JPEG |
| Quality | `95` |
| Chroma subsampling | `0` (4:4:4) |
| Optimization | Enabled |
| Resampling | LANCZOS |
| Background for transparency | White |

These settings favor visual quality. **Output file size in megabytes is not fixed**, and conversion to JPEG is generally lossy even if the source image was already JPEG or did not need resizing. JPEG does not support alpha transparency or animation.

## Very large images and memory use

The script sets:

```python
Image.MAX_IMAGE_PIXELS = 300_000_000
```

With Pillow's default decompression-bomb handling, images over this configured threshold may trigger a warning, while those over twice the threshold (600 million pixels) raise an error. This protects against unexpectedly huge or malicious images, although **300 MP is not a memory limit**.

For reference, a 200 MP image can require roughly **600 MB of memory in RGB** or **800 MB in RGBA** just for its decoded pixel buffer. Processing can require substantially more RAM due to intermediate data and resampling. Work with trusted source files and ensure sufficient system memory.

The current implementation does not use JPEG decoder scaling (`draft()`) or other memory-saving streaming techniques.

## Troubleshooting

### `exiftool` not found

Install ExifTool separately, confirm its installation directory is on PATH, and check:

```bash
exiftool -ver
```

### `ModuleNotFoundError: No module named 'PIL'`

Install Pillow in the same Python environment used to run the script:

```bash
python -m pip install pillow
```

### `ModuleNotFoundError: No module named 'pillow_heif'`

```bash
python -m pip install pillow-heif
```

### `DecompressionBombError` or an image-size warning

The source image may be larger than the safety thresholds. Verify that it comes from a trusted source before changing `Image.MAX_IMAGE_PIXELS`. Extremely large images may also exhaust available RAM.

### An image is shown as `[SKIPPED]`

Check whether the JPEG already exists in the destination, or whether another source file has the same filename stem.

### Metadata differs from the source

Not all tags can be represented or written in JPEG. Check any `[METADATA WARNING]` messages and inspect both files with ExifTool. Also note that the output is re-encoded and its orientation and pixel dimensions are intentionally changed when necessary.

### Images look different after conversion

JPEG is lossy and cannot retain transparency. Additionally, uncommon color profiles or color modes may need extra color-management handling; the current script is not a fully color-managed conversion pipeline.

## Current limitations

- No recursive processing of subdirectories.
- No parallel batch processing or progress bar.
- No output format other than JPEG.
- No guarantee of complete preservation of every proprietary metadata tag.
- No guaranteed preservation of embedded ICC profiles/color appearance across formats.
- No video, animated-image, Live Photo, or multi-page-document workflow; the current script processes the default opened image/frame.
- Existing destination files are never automatically replaced.
- No automatic deduplication based on file content.

## Suggested repository structure

```text
image-resizer/
├── resize_images.py
├── README.md
├── LICENSE
└── .gitignore
```

A minimal `.gitignore` could contain:

```gitignore
.venv/
__pycache__/
*.py[cod]
originals/
output/
```

## License

This project is licensed under the [MIT License](LICENSE). See the `LICENSE` file for the full terms.

Before publishing, replace `[Your Name or Organization]` in `LICENSE` with the copyright holder’s name.

## Acknowledgments

- [Pillow](https://pillow.readthedocs.io/) — image decoding, resampling, and JPEG encoding.
- [pillow-heif](https://pillow-heif.readthedocs.io/) — HEIC/HEIF support for Pillow.
- [ExifTool](https://exiftool.org/) — image metadata reading and writing.

---

**Important:** Always keep a backup of your original photographs. This tool creates separate outputs, but metadata transfer and JPEG conversion are not guaranteed to preserve every property of every source file.
