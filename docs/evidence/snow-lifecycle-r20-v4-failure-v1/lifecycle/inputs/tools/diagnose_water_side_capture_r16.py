"""Show logical side sample coordinates on retained captures; no game calls."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from analyze_water_acceptance_r16 import side_grid, side_sample


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = json.loads(args.source.read_bytes())
    for route in source['routes']:
        label = route + '_pool_wet'
        row = source['rows'][label]
        shapes = {tuple(shape['position']): shape for shape in row['ready']['shapes']
                  if shape['texture'] == 'flowing_water_grey' and shape['faces'] & 30}
        original = Image.open(source['captures'][label]['path']).convert('RGB')
        image = np.asarray(original)
        marked = original.copy()
        draw = ImageDraw.Draw(marked)
        samples = []
        for face, positions in ((2, ((3, 3, 4), (4, 3, 4))), (4, ((4, 3, 3), (4, 3, 4)))):
            for position, color in zip(positions, ('#ff3333', '#33ff33')):
                shape = shapes[position]
                dimensions, coordinates = side_grid(image, shape, face, row, source)
                for x, y in coordinates:
                    draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=color)
                samples.append(Image.fromarray(np.rint(side_sample(image, shape, face, row, source)).astype('uint8')).resize((180, 140)))
        marked.save(args.output / (route + '-mapped.png'))
        contact = Image.new('RGB', (360, 280))
        for index, sample in enumerate(samples):
            contact.paste(sample, ((index % 2) * 180, (index // 2) * 140))
        contact.save(args.output / (route + '-samples.png'))


if __name__ == '__main__':
    main()
