import zipfile
import io
from typing import Union
from pathlib import Path

from PIL import Image

__all__ = [
    'zip_output_images',
    'save_output_images',
]

STACKABLE_IMAGE_FORMATS = ('pdf', 'tiff')
DEFAULT_IMAGE_FORMAT_NONSTACKED = 'png'
DEFAULT_IMAGE_FORMAT_STACKED = 'pdf'


def zip_output_images(
        images: list[Image.Image],
        fp: Union[str, Path] = None,
        image_format: str = None,
        stack: bool = None,
        twprges: list[str] = None
) -> None:
    """
    INTERNAL USE:

    Save the images to a .zip file, either separately or as a single
    stacked image.

    :param images: A list of ``PIL.Image.Image`` objects, as given by
        any ``.output()`` method.
    :param fp: (See docs for ``PlatGroup.output()``.)
    :param image_format: (See docs for ``PlatGroup.output()``.)
    :param stack: (See docs for ``PlatGroup.output()``.)
    :param twprges: (Optional) List of Twp/Rge strings to add to the
        end of filenames if more than one image is to be written.
    """
    if isinstance(images, Image.Image):
        images = [images]
    if image_format is None:
        if stack:
            image_format = DEFAULT_IMAGE_FORMAT_STACKED
        else:
            image_format = DEFAULT_IMAGE_FORMAT_NONSTACKED

    if stack:
        im_bytes = io.BytesIO()
        im = images[0]
        im.save(im_bytes, format=image_format, save_all=True, append_images=images[1:])
        fn = f"{fp.stem}.{image_format}"
        im_bytes.seek(0)
        with zipfile.ZipFile(fp, 'w') as zfile:
            zfile.writestr(fn, im_bytes.getvalue())
        return None

    just = len(images) % 10
    with zipfile.ZipFile(fp, 'w') as zfile:
        for i, im in enumerate(images, start=0):
            surplus = str(i + 1).rjust(just, '0')
            if twprges is not None:
                surplus = twprges[i]
            fn = f"{fp.stem} {surplus}.{image_format}"
            im_bytes = io.BytesIO()
            im.save(im_bytes, format=image_format)
            im_bytes.seek(0)
            zfile.writestr(fn, im_bytes.getvalue())
    return None


def save_output_images(
        images: list[Image.Image],
        fp: Union[str, Path] = None,
        image_format: str = None,
        stack: bool = None,
        twprges: list[str] = None,
) -> None:
    """
    Save the images to disk as one or more separate image files; or
    into a .zip file (if the file extension of ``fp`` is ``.zip``).

    :param images: A list of ``PIL.Image.Image`` objects, as given by
        any ``.output()`` method.
    :param fp: (See docs for ``PlatGroup.output()``.)
    :param image_format: (See docs for ``PlatGroup.output()``.)
    :param stack: (See docs for ``PlatGroup.output()``.)
    :param twprges: (Optional) List of Twp/Rge strings to add to the
        end of filenames if more than one image is to be written.
    """
    if isinstance(images, Image.Image):
        images = [images]
    fp = Path(fp)
    fp.parent.mkdir(exist_ok=True)
    sfx = fp.suffix.lower()

    cand_fmt = sfx[1:]
    if cand_fmt != 'zip':
        if image_format is None:
            image_format = cand_fmt
        if image_format.lower() != cand_fmt:
            raise ValueError(
                f"File suffix {cand_fmt!r} "
                f"does not match image format {image_format!r}")
    if stack and image_format not in STACKABLE_IMAGE_FORMATS:
        raise ValueError(
            f"Cannot stack with image format {image_format!r}. "
            f"Acceptable formats: {', '.join(STACKABLE_IMAGE_FORMATS)}"
        )
    if stack is None and image_format in STACKABLE_IMAGE_FORMATS:
        # Assume user wants to stack any formats that allow it.
        stack = True
    if sfx == '.zip':
        # Handle .zip files separately.
        return zip_output_images(images, fp, image_format, stack, twprges)

    n = len(images)
    just = n % 10
    if n == 1:
        im = images[0]
        im.save(fp, format=image_format)
        return None
    elif stack:
        im = images[0]
        im.save(fp, format=image_format, save_all=True, append_images=images[1:])
        return None
    else:
        for i, im in enumerate(images, start=0):
            surplus = str(i + 1).rjust(just, '0')
            if twprges is not None:
                surplus = twprges[i]
            fn = f"{fp.stem} {surplus}.{image_format}"
            im.save(fp.with_name(fn), format=image_format)
    return None
