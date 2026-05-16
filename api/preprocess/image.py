from __future__ import annotations
import io
from PIL import Image, ImageOps

def preprocessImage(data,size=1024,quality=85):
    if not data:
        raise ValueError("Empty image payload.")
    try:
        with Image.open(io.BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode != "RGB":
                img = img.convert("RGB")
            square = ImageOps.fit(
                img,
                (size, size),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            buffer = io.BytesIO()
            square.save(
                buffer,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True,
            )
            return buffer.getvalue()
    except (OSError, ValueError) as exc:
        raise ValueError(f"Could not decode image: {exc}") from exc