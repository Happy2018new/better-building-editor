"""Local native outline gates prevent a small clipped tip hiding in a large body."""
import math

import numpy as np
from PIL import Image, ImageFilter

from analyze_item_sprite_product import expanded
from analyze_item_sprite_closeup import NATIVE_BODY_LIMITS
from analyze_liquid_workspace import mask_row

EDGE_LIMITS = {'edge_tolerance_pixels': 2, 'minimum_local_recall': .985,
               'minimum_local_native_pixels': 8, 'perimeter_band_pixels': 3,
               'tile_pixels': 24, 'terminal_fraction': .125}


def native_edge_measurement(product, reference):
    """Score each native terminal and perimeter region without moving either mask.

    The same two-pixel screen tolerance as the whole-body gate applies. Native
    endpoints and fixed local perimeter tiles are scored individually, so a
    frame overlapping the sword tip cannot be averaged away by its full blade.
    No frame color assumptions, fitted translation, or candidate-shaped ROI is
    used. The minimum screen extent remains the native body gate's 48 pixels.
    """
    if product.shape != reference.shape or product.dtype != bool or reference.dtype != bool:
        raise ValueError('Native edge masks must be same-size boolean images')
    bounds = mask_row(reference)['bounds']
    result = {'limits': EDGE_LIMITS, 'native': mask_row(reference), 'regions': [], 'passed': False}
    if bounds is None:
        return result
    left, top, right, bottom = bounds
    if min(right-left, bottom-top) < NATIVE_BODY_LIMITS['minimum_extent_pixels']:
        return result
    tolerance = EDGE_LIMITS['edge_tolerance_pixels']
    product_tolerant = expanded(product, tolerance*2+1)
    eroded = np.asarray(Image.fromarray((reference*255).astype(np.uint8)).filter(
        ImageFilter.MinFilter(EDGE_LIMITS['perimeter_band_pixels']*2+1))) > 0
    perimeter = reference & ~eroded
    def region(label, box, selected):
        x0, y0, x1, y1 = box
        native = selected[y0:y1, x0:x1]
        count = int(native.sum())
        if count < EDGE_LIMITS['minimum_local_native_pixels']:
            return
        recalled = int((native & product_tolerant[y0:y1, x0:x1]).sum())
        recall = recalled/count
        result['regions'].append({'label': label, 'box': list(box), 'native_pixels': count,
            'missing_beyond_2px': count-recalled, 'recall': recall,
            'passed': recall >= EDGE_LIMITS['minimum_local_recall']})
    dx = max(4, int(math.ceil((right-left)*EDGE_LIMITS['terminal_fraction'])))
    dy = max(4, int(math.ceil((bottom-top)*EDGE_LIMITS['terminal_fraction'])))
    for label, box in (('left', (left,top,left+dx,bottom)), ('right', (right-dx,top,right,bottom)),
                       ('top', (left,top,right,top+dy)), ('bottom', (left,bottom-dy,right,bottom))):
        region('terminal_'+label, box, reference)
    step = EDGE_LIMITS['tile_pixels']
    for y in range(top, bottom, step):
        for x in range(left, right, step):
            region('perimeter_%d_%d' % (x-left,y-top), (x,y,min(x+step,right),min(y+step,bottom)), perimeter)
    result['passed'] = bool(result['regions']) and all(row['passed'] for row in result['regions'])
    return result
