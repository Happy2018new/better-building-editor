"""Compare actual native closed boxes with render proxies at a matching camera."""
import math
from collections import deque

from PIL import Image, ImageChops, ImageFilter, ImageOps

SCHEMA_VERSION = 1


def purple_mask(image):
    red, green, blue = image.convert('RGB').split()
    first = ImageChops.subtract(red, green).point(lambda value: 255 if value > 14 else 0)
    second = ImageChops.subtract(blue, green).point(lambda value: 255 if value > 14 else 0)
    brightness = ImageChops.lighter(red, blue).point(lambda value: 255 if value > 40 else 0)
    return ImageChops.multiply(ImageChops.multiply(first, second), brightness)


def central_object(image, minimum=150):
    """Isolate the central box instead of nearby fixtures or purple HUD pixels."""
    mask = purple_mask(image).filter(ImageFilter.MaxFilter(3))
    width, height = mask.size
    pixels = bytearray(mask.tobytes())
    components = []
    for seed, value in enumerate(pixels):
        if not value:
            continue
        pixels[seed] = 0
        queue, members = deque((seed,)), []
        left = right = seed % width
        top = bottom = seed // width
        while queue:
            index = queue.popleft()
            members.append(index)
            x, y = index % width, index // width
            left, right = min(left, x), max(right, x)
            top, bottom = min(top, y), max(bottom, y)
            neighbors = []
            if x:
                neighbors.append(index - 1)
            if x + 1 < width:
                neighbors.append(index + 1)
            if y:
                neighbors.append(index - width)
            if y + 1 < height:
                neighbors.append(index + width)
            for neighbor in neighbors:
                if pixels[neighbor]:
                    pixels[neighbor] = 0
                    queue.append(neighbor)
        if len(members) >= minimum:
            distance = ((left + right + 1) / 2 - width / 2) ** 2 + ((top + bottom + 1) / 2 - height / 2) ** 2
            components.append((distance, members, (left, top, right + 1, bottom + 1)))
    if not components:
        raise AssertionError('No central Shulker model has at least %d purple pixels' % minimum)
    distance, members, box = min(components, key=lambda row: row[0])
    if distance > (min(width, height) * .2) ** 2:
        raise AssertionError('Shulker model is outside the fixed camera center: %r' % (box,))
    selected = bytearray(width * height)
    for index in members:
        selected[index] = 255
    selected = Image.frombytes('L', image.size, bytes(selected))
    result = Image.new('RGB', image.size, 'black')
    result.paste(image.convert('RGB'), mask=selected)
    return result, selected, {'purple_pixels': len(members), 'bbox': box,
                              'nearby_components_ignored': len(components) - 1}


def normalized_object(frame, size=64):
    image, mask, record = central_object(frame)
    box = record['bbox']
    resampling = getattr(Image, 'Resampling', Image)
    return (image.crop(box).resize((size, size), resampling.BILINEAR),
            mask.crop(box).resize((size, size), resampling.NEAREST), record)


def pair_comparison(native, proxy):
    return _prepared_pair(normalized_object(native), normalized_object(proxy))


def _prepared_pair(native, proxy):
    first, first_mask, first_record = native
    second, second_mask, second_record = proxy
    intersection = ImageChops.multiply(first_mask, second_mask)
    union = ImageChops.lighter(first_mask, second_mask)
    iou = intersection.histogram()[255] / float(union.histogram()[255])
    width, height = intersection.size
    interior = ImageOps.expand(intersection, border=4, fill=0).filter(ImageFilter.MinFilter(9)).crop(
        (4, 4, width + 4, height + 4))
    eligible = list(interior.tobytes())
    features = []
    for image in (first, second):
        blurred = image.filter(ImageFilter.BoxBlur(3))
        channels, low = image.split(), blurred.split()
        features.append([actual - smoothed for channel, smoothed_channel in zip(channels, low)
                         for actual, smoothed, use in zip(channel.tobytes(), smoothed_channel.tobytes(), eligible)
                         if use])
    energies = [sum(value * value for value in feature) for feature in features]
    cosine = None
    if all(energy > 100 for energy in energies):
        cosine = sum(left * right for left, right in zip(*features)) / math.sqrt(energies[0] * energies[1])
    dimensions = []
    for record in (first_record, second_record):
        box = record['bbox']
        dimensions.append((box[2] - box[0], box[3] - box[1]))
    scale_error = max(abs(right / float(left) - 1) for left, right in zip(*dimensions))
    return {'shape_iou': iou, 'texture_cosine': cosine,
            'scale_relative_error': scale_error,
            'native_bbox': first_record['bbox'], 'proxy_bbox': second_record['bbox'],
            'texture_samples': len(features[0]), 'texture_energy': energies}


def native_proxy_comparison(native, proxy, minimum_iou=.82, minimum_texture=.45,
                            maximum_scale_error=.2, alternative_margin=.03):
    if len(native) != 6 or len(proxy) != 6:
        raise AssertionError('Six real native references and six proxy images are required')
    references = [normalized_object(frame) for frame in native]
    projected = [normalized_object(frame) for frame in proxy]
    matrix = [[_prepared_pair(left, right) for right in projected] for left in references]
    rows = []
    for facing in range(6):
        record = dict(matrix[facing][facing], facing=facing)
        scores = [row['texture_cosine'] for row in matrix[facing]]
        best = max((score for score in scores if score is not None), default=None)
        record['best_proxy_faces'] = [] if best is None else [
            index for index, score in enumerate(scores)
            if score is not None and score >= best - alternative_margin]
        record['passed'] = (record['shape_iou'] >= minimum_iou and
                            record['scale_relative_error'] <= maximum_scale_error and
                            record['texture_cosine'] is not None and
                            record['texture_cosine'] >= minimum_texture and
                            facing in record['best_proxy_faces'])
        rows.append(record)
    return {'schema_version': SCHEMA_VERSION, 'passed': all(row['passed'] for row in rows),
            'same_face': rows, 'cross_face_texture_cosine': [
                [row['texture_cosine'] for row in scores] for scores in matrix],
            'thresholds': {'shape_iou': minimum_iou, 'texture_cosine': minimum_texture,
                           'scale_relative_error': maximum_scale_error,
                           'alternative_margin': alternative_margin},
            'scope': 'Same-camera native world pixels versus actual projection pixels; '
                     'closed-box silhouette and local texture contrast. Symmetric faces may tie.'}
