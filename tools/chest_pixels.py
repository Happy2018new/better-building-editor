"""Independent visible-object extraction for native and proxy chest captures."""
from PIL import Image, ImageChops
from verify_camera_projection import largest_component
from verify_missing_neighbor_visuals import maximum


def object_frame(shown, empty, output):
    with Image.open(shown).convert('RGB') as image, Image.open(empty).convert('RGB') as background:
        if image.size != background.size:
            raise AssertionError('Native and proxy viewport differ')
        width, height = image.size
        crop = (int(width * .25), int(height * .2), int(width * .75), int(height * .8))
        first = image.crop(crop)
        delta = maximum(ImageChops.difference(image, background)).crop(crop)
    mask = largest_component(delta.point(lambda value: 255 if value > 25 else 0))
    count, bounds = mask.histogram()[255], mask.getbbox()
    if count < 1000 or bounds is None:
        raise AssertionError('No central chest model contributes 1000 pixels: %r' % count)
    selected = Image.new('RGB', first.size)
    selected.paste(first, mask=mask)
    selected.save(output)
    resampling = getattr(Image, 'Resampling', Image)
    return (selected.crop(bounds).resize((64, 64), resampling.BILINEAR),
            mask.crop(bounds).resize((64, 64), resampling.NEAREST),
            {'bbox': bounds, 'pixels': count, 'crop': crop, 'mask': str(output.resolve())})
