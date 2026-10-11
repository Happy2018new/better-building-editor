"""Inspect fingerprinted native alpha rows without changing render candidates."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from generate_static_plant_proxies import SOURCE, CANDIDATES, validate
from projection.debug_snow_blueprints import VISUAL_CASE


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(native, output):
    if output.exists():
        raise ValueError('Choose a fresh evidence filename: '+str(output))
    source = json.loads(SOURCE.read_text(encoding='utf8'))
    validate(source, native)
    public = {row['plant']: row for row in VISUAL_CASE['cells']}
    rows = []
    sheet = Image.new('RGB', (6*224, 4*232), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    for index, (name, record) in enumerate(sorted(source['plants'].items())):
        path = native/record['texture_path']
        with Image.open(path) as loaded:
            texture = loaded.convert('RGBA')
        alpha = texture.getchannel('A')
        width, height = texture.size
        counts = [sum(alpha.getpixel((x, y)) > 0 for x in range(width))
                  for y in range(height)]
        occupied = [y for y, value in enumerate(counts) if value]
        max_y = 1.-occupied[0]/float(height)
        rows.append({'plant': name, 'texture_path': str(path.resolve()),
                     'texture_sha256': digest(path), 'texture_size': texture.size,
                     'alpha_bounds': alpha.getbbox(), 'alpha_nonzero_pixels_by_row': counts,
                     'alpha_values': sorted(set(alpha.getdata())),
                     'unshifted_unit_cross_max_y': max_y,
                     'first_fully_buried_height': next((value for value in range(8)
                                                      if (value+1)/8. >= max_y), None),
                     'public_blueprint': {'fixture': VISUAL_CASE['fixture'],
                                          'fixture_schema': VISUAL_CASE['schema'],
                                          'standalone': public[name]['standalone'],
                                          'covered': public[name]['covered'],
                                          'support': public[name]['support']}})
        left, top = (index%6)*224, (index//6)*232
        tile = Image.new('RGBA', (160, 160))
        checker = ImageDraw.Draw(tile)
        for y in range(0, 160, 10):
            for x in range(0, 160, 10):
                color = (205, 205, 205, 255) if (x+y)//10%2 else (235, 235, 235, 255)
                checker.rectangle((x, y, x+9, y+9), fill=color)
        tile.alpha_composite(texture.resize((160, 160), Image.Resampling.NEAREST))
        sheet.paste(tile.convert('RGB'), (left+24, top+20))
        draw.text((left+12, top+188), name, fill=(20, 20, 20))
        draw.text((left+12, top+205), 'maxY='+str(max_y), fill=(20, 20, 20))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet_path = output.with_name(output.stem+'_native_textures.png')
    sheet.save(sheet_path)
    report = {'schema': 1, 'game_version': source['game_version'],
              'palette_sha256': source['palette_sha256'],
              'source_snapshot': {'path': str(SOURCE.resolve()), 'sha256': digest(SOURCE)},
              'mapping_sources': {key: {'path': str((native/source['paths'][key]).resolve()),
                                       'sha256': source['sha256'][key]}
                                  for key in ('blocks', 'terrain')},
              'public_blueprint': VISUAL_CASE['fixture'], 'plants': rows,
              'pending_after_mushrooms': sorted(set(source['plants'])-CANDIDATES),
              'excluded_special_families': source['excluded'],
              'contact_sheet': {'path': str(sheet_path.resolve()), 'sha256': digest(sheet_path)},
              'method': 'Unmodified native RGBA textures, all nonzero alpha values; Y=(16-row)/16 on an unshifted unit-height cross',
              'render_candidate_contract': source['geometry_contract'],
              'acceptance': {'render_pixels_passed': False,
                             'required': ['independent native dry positive', 'snow occlusion negative',
                                          'public blueprint editor', 'full projection', 'missing projection',
                                          'all heights', 'frozen assets', 'cleanup']}}
    output.write_text(json.dumps(report, ensure_ascii=True, indent=2)+'\n', encoding='utf8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--native-resource-root', type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.native_resource_root, args.output)
    print(json.dumps({'plants': len(report['plants']),
                      'pending_after_mushrooms': len(report['pending_after_mushrooms']),
                      'output': str(args.output.resolve())}))


if __name__ == '__main__':
    main()
