"""Blank-frame sign board isolation and fixed-cutoff baseline controls."""
from PIL import Image, ImageChops, ImageDraw


def wooden_rectangle(blank, crop):
    """Find the largest solid wood rectangle without merging separate row runs."""
    with Image.open(blank) as source:
        image = source.convert('RGB').crop(crop)
    heights = [0] * image.width
    best = None
    best_area = 0
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            wood = red > green * 1.10 and green > blue * 1.10 and red > 35
            heights[x] = heights[x] + 1 if wood else 0
        # Histogram rectangles preserve gaps between terrain and the board.
        stack = []
        for right, height in enumerate(heights + [0]):
            left = right
            while stack and stack[-1][1] > height:
                left, previous = stack.pop()
                area = (right - left) * previous
                if area > best_area:
                    best_area = area
                    best = (left, y + 1 - previous, right, y + 1)
            if height and (not stack or stack[-1][1] < height):
                stack.append((left, height))
    return best


def isolate(mask, panel):
    result = Image.new('L', mask.size)
    if panel:
        result.paste(mask.crop(panel), panel)
    return result


def baseline_control(first, second, crop, panel, output, excluded=None):
    with Image.open(first) as source, Image.open(second) as reference:
        delta = ImageChops.difference(source.convert('RGB').crop(crop),
                                     reference.convert('RGB').crop(crop))
    red, green, blue = delta.split()
    signal = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    support = Image.new('L', delta.size)
    if panel:
        ImageDraw.Draw(support).rectangle((panel[0], panel[1], panel[2] - 1, panel[3] - 1), fill=255)
    if excluded:
        ImageDraw.Draw(support).rectangle((excluded[0], excluded[1], excluded[2] - 1, excluded[3] - 1), fill=0)
    selected = ImageChops.multiply(signal.point(lambda value: 255 if value > 20 else 0), support)
    selected.save(output)
    maximum = ImageChops.multiply(signal, support).getextrema()[1]
    changed = selected.histogram()[255]
    return {'determinate': panel is not None, 'passed': panel is not None and changed == 0,
            'minimum_difference': 20, 'allowed_changed_pixels': 0,
            'support_pixels': support.histogram()[255], 'changed_pixels': changed,
            'maximum_channel_difference': maximum, 'panel_bounds': panel,
            'excluded_text_bounds': excluded, 'mask': str(output.resolve())}


def corresponding_text(native_bounds, native_panel, panel, margin=2):
    if not all((native_bounds, native_panel, panel)):
        return None
    result = []
    for axis in range(4):
        dimension = axis % 2
        fraction = (native_bounds[axis] - native_panel[dimension]) / (
            native_panel[dimension + 2] - native_panel[dimension])
        value = panel[dimension] + fraction * (panel[dimension + 2] - panel[dimension])
        result.append(round(value) + (-margin if axis < 2 else margin))
    return tuple(result)
