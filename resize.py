from pathlib import Path
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
import argparse
import math
import shutil
import subprocess
import tempfile
import os

# Allow large images up to 300 megapixels without warnings.
Image.MAX_IMAGE_PIXELS = 300_000_000

# Enable HEIC / HEIF support.
register_heif_opener()

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif",
    ".tif", ".tiff", ".webp", ".bmp"
}

JPEG_QUALITY = 95


def copy_metadata(source, destination, width, height):
    """
    Copy compatible metadata from the original image
    to the output JPEG using ExifTool.

    Preserve shooting date, camera information, GPS,
    exposure settings, and other supported metadata.
    Update orientation and image dimensions.
    """

    command = [
        "exiftool",
        "-overwrite_original",
        "-TagsFromFile", str(source),
        "-all",
        "-Orientation#=1",
        f"-ExifIFD:ExifImageWidth={width}",
        f"-ExifIFD:ExifImageHeight={height}",
        str(destination)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Metadata transfer failed: {result.stderr.strip()}"
        )

    if result.stderr.strip():
        print(f"  [METADATA WARNING] {result.stderr.strip()}")


def process_image(source, destination, target_mp=8):
    """
    Convert an image to JPEG, resizing it only when
    its resolution exceeds the specified megapixel limit.

    Preserve metadata through ExifTool.
    """

    target_pixels = target_mp * 1_000_000

    # Create a temporary JPEG in the output directory.
    # It will be moved to its final name only on success.
    fd, temp_path = tempfile.mkstemp(
        suffix=".jpg",
        dir=destination.parent
    )
    os.close(fd)
    temp_path = Path(temp_path)

    try:
        with Image.open(source) as img:
            # Apply EXIF orientation to the image pixels.
            img = ImageOps.exif_transpose(img)

            width, height = img.size
            original_mp = width * height / 1_000_000

            if width * height > target_pixels:
                scale = math.sqrt(
                    target_pixels / (width * height)
                )

                new_width = max(1, int(width * scale))
                new_height = max(1, int(height * scale))

                img = img.resize(
                    (new_width, new_height),
                    Image.Resampling.LANCZOS
                )

                status = "RESIZED"
            else:
                status = "CONVERTED"

            # Handle transparent images using a white background.
            if img.mode in ("RGBA", "LA") or (
                img.mode == "P"
                and "transparency" in img.info
            ):
                img = img.convert("RGBA")

                background = Image.new(
                    "RGB", img.size, (255, 255, 255)
                )

                background.paste(
                    img,
                    mask=img.getchannel("A")
                )

                img = background

            elif img.mode != "RGB":
                img = img.convert("RGB")

            final_width, final_height = img.size
            final_mp = (
                final_width * final_height / 1_000_000
            )

            # Save image pixels as JPEG.
            img.save(
                temp_path,
                format="JPEG",
                quality=JPEG_QUALITY,
                subsampling=0,
                optimize=True
            )

        # Restore metadata from the original image.
        copy_metadata(
            source,
            temp_path,
            final_width,
            final_height
        )

        # Preserve file timestamps and permissions
        # where supported by the operating system.
        shutil.copystat(source, temp_path)

        # Move the completed JPEG to its final location.
        os.replace(temp_path, destination)

        print(
            f"[{status}] {source.name} -> {destination.name} | "
            f"{original_mp:.2f} MP -> {final_mp:.2f} MP "
            f"({final_width}x{final_height}) | "
            f"Metadata transferred"
        )

    finally:
        # Remove temporary files if an error occurs.
        if temp_path.exists():
            temp_path.unlink()


def process_folder(input_folder, output_folder, target_mp=8):
    """
    Process all supported images in the source directory.
    Save JPEG copies to the destination directory.
    """

    input_folder = Path(input_folder).resolve()
    output_folder = Path(output_folder).resolve()

    if not input_folder.is_dir():
        raise ValueError("Input directory does not exist.")

    if input_folder == output_folder:
        raise ValueError(
            "Input and output directories must be different."
        )

    if shutil.which("exiftool") is None:
        raise RuntimeError(
            "ExifTool was not found. "
            "Please install ExifTool and add it to PATH."
        )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    images = sorted(
        file for file in input_folder.iterdir()
        if file.is_file()
        and file.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    print(f"Images found: {len(images)}")
    print(f"Maximum resolution: {target_mp} MP")
    print("Output format: JPEG")
    print("Metadata preservation: Enabled\n")

    processed = 0
    errors = 0
    skipped = 0
    used_names = set()

    for source in images:
        destination = output_folder / f"{source.stem}.jpg"

        # Prevent filename collisions caused by
        # different source formats sharing the same stem.
        output_name = destination.name.casefold()

        if output_name in used_names:
            print(
                f"[SKIPPED] {source.name}: "
                "Duplicate output filename."
            )
            skipped += 1
            continue

        used_names.add(output_name)

        # Never overwrite existing output files.
        if destination.exists():
            print(
                f"[SKIPPED] {source.name}: "
                "Output file already exists."
            )
            skipped += 1
            continue

        try:
            process_image(
                source,
                destination,
                target_mp
            )
            processed += 1

        except Exception as e:
            print(f"[ERROR] {source.name}: {e}")
            errors += 1

    print("\nProcessing completed.")
    print(f"Successfully processed: {processed}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Convert images to JPEG with a maximum "
            "resolution and preserve original metadata."
        )
    )

    parser.add_argument(
        "input",
        help="Source directory containing original images"
    )

    parser.add_argument(
        "output",
        help="Destination directory for processed JPEG images"
    )

    parser.add_argument(
        "--mp",
        type=float,
        default=8,
        help="Maximum megapixels (default: 8)"
    )

    args = parser.parse_args()

    if not math.isfinite(args.mp) or args.mp <= 0:
        parser.error(
            "--mp must be a finite number greater than zero."
        )

    process_folder(
        args.input,
        args.output,
        args.mp
    )
