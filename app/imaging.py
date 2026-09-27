"""Image validation, EXIF removal, quality feedback and exact model preprocessing."""
from io import BytesIO
import warnings
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 20_000_000
MAX_FILE_BYTES = 6 * 1024 * 1024

class ImageProblem(ValueError):
    pass

def decode_image(data: bytes):
    if not data or len(data) > MAX_FILE_BYTES:
        raise ImageProblem("Each photo must be under 6 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ImageProblem("Choose a JPEG, PNG or WebP photo.")
                if getattr(source, "n_frames", 1) != 1:
                    raise ImageProblem("Use a still photo, not an animation.")
                if source.width * source.height > Image.MAX_IMAGE_PIXELS:
                    raise ImageProblem("This photo is too large. Export it below 20 megapixels.")
                rgb = ImageOps.exif_transpose(source).convert("RGB")
                rgb.load()
    except ImageProblem:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ImageProblem("This file could not be read as a safe photo. Try another JPEG or PNG.") from None
    if min(rgb.size) < 128:
        raise ImageProblem("This photo is too small. Use a photo at least 128 pixels on each side.")
    # Rebuild pixels to remove EXIF, GPS and any other embedded image metadata.
    clean = Image.fromarray(np.asarray(rgb))
    return clean

def quality(image):
    gray = np.asarray(ImageOps.grayscale(image).resize((256, 256)), dtype=np.float32)
    lap = -4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    sharpness, contrast, brightness = float(lap.var()), float(gray.std()), float(gray.mean())
    messages = []
    if brightness < 35:
        messages.append("The photo is dark. Try open shade in daylight.")
    if brightness > 225:
        messages.append("The photo is very bright. Avoid glare and flash.")
    if sharpness < 24:
        messages.append("Details look soft. Hold the camera still and tap the leaf to focus.")
    if contrast < 10:
        messages.append("There is very little visible detail. Fill the frame with one leaf.")
    blocked = contrast < 5 or sharpness < 3 or brightness < 15 or brightness > 248
    return {"usable": not blocked, "warnings": messages,
            "brightness": round(brightness, 1), "sharpness": round(sharpness, 1),
            "note": "These checks assess photo quality; they do not verify that an image contains a leaf."}

def preprocess(image, config):
    size = int(config["size"])
    resize_short = int(config["resize_short"])
    w, h = image.size
    if w <= h:
        dims = (resize_short, int(resize_short * h / w))
    else:
        dims = (int(resize_short * w / h), resize_short)
    img = image.resize(dims, Image.Resampling.BILINEAR)
    left, top = round((img.width - size) / 2), round((img.height - size) / 2)
    img = img.crop((left, top, left + size, top + size))
    arr = np.asarray(img, dtype=np.float32) / np.float32(255)
    arr = (arr - np.array(config["mean"], np.float32)) / np.array(config["std"], np.float32)
    return np.ascontiguousarray(arr.transpose(2, 0, 1)[None], dtype=np.float32)

def clean_jpeg(image):
    copy = image.copy()
    copy.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    stream = BytesIO()
    copy.save(stream, "JPEG", quality=90)
    return stream.getvalue()
