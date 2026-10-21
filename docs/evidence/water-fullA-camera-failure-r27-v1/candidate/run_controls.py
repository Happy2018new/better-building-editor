"""Actual old-raw replay plus declared image perturbations; no MC or refitting."""
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image,ImageDraw

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[2]
HOST=WORK.with_name('water-merged-fullA-v1')
PROJECT=ROOT/'.runtime/projects/water-r27-merged-flow-editor-v1'
sys.path.insert(0,str(PROJECT/'tools'))
import verify_camera_projection as original
sys.path.insert(0,str(WORK))
import candidate_extractor as candidate


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fit_passed(fit):
    return (fit['boundary_rms_pixels']<=2 and fit['mask_iou']>=.95 and
        fit['outline_recall_2px']>=.985 and fit['outline_precision_2px']>=.985)


def main():
    out=WORK/'controls-v1'
    out.mkdir(exist_ok=False)
    source=HOST/'product-v2-camera-native-v1.json'
    source_raw=source.read_bytes()
    source_data=json.loads(source_raw)
    fov=source_data['vertical_fov']
    rows=[]
    originals={str(source):sha(source_raw)}
    for row in source_data['views']:
        for item in (row['shown'],row['hidden']):
            path=Path(item['path'])
            assert sha(path.read_bytes())==item['sha256']
            originals[str(path)]=item['sha256']
        facts={}
        mask=candidate.stone_signal(row['shown']['path'],row['hidden']['path'],facts)
        fit=original.fit_fov(mask,row['pose'],fov)
        mask_path=out/(row['view']+'-candidate-mask.png')
        mask.save(mask_path)
        rows.append({'name':'actual_'+row['view'],'expected_passed':True,
            'candidate_passed':fit_passed(fit),'fit':fit,'extractor_observations':facts,
            'candidate_mask_sha256':sha(mask_path.read_bytes()),
            'original_view_passed':row['passed'],'original_fit':row['fit']})
    tilted=next(row for row in source_data['views'] if row['view']=='tilted')
    original_shown=Image.open(tilted['shown']['path']).convert('RGB')
    hidden=Image.open(tilted['hidden']['path']).convert('RGB')
    bounds=(595,307,686,417)

    def test(name,mutate):
        image=original_shown.copy()
        mutate(image)
        image_path=out/(name+'-shown.png')
        image.save(image_path)
        record={'name':name,'expected_passed':False,'synthetic_image_perturbation':True,
            'shown_sha256':sha(image_path.read_bytes()),'candidate_passed':False}
        facts={}
        try:
            mask=candidate.stone_signal(image_path,tilted['hidden']['path'],facts)
            fit=original.fit_fov(mask,tilted['pose'],fov)
            record.update(candidate_passed=fit_passed(fit),fit=fit)
        except AssertionError as error:
            record['rejection']=str(error)
        record['extractor_observations']=facts
        rows.append(record)

    test('real_top_removed',lambda image:image.paste(hidden.crop((595,307,686,340)),(595,307)))

    def move(image,dx,dy):
        patch=image.crop(bounds)
        image.paste(hidden.crop(bounds),bounds[:2])
        image.paste(patch,(bounds[0]+dx,bounds[1]+dy))
    test('cube_moved_x_12',lambda image:move(image,12,0))
    test('cube_moved_y_12',lambda image:move(image,0,12))

    def scale(image):
        patch=image.crop(bounds)
        image.paste(hidden.crop(bounds),bounds[:2])
        patch=patch.resize((int(patch.width*1.25),int(patch.height*1.25)),Image.Resampling.NEAREST)
        image.paste(patch,(640-patch.width//2,362-patch.height//2))
    test('tilted_cube_scaled_1_25',scale)
    test('extra_independent_stone_patch',lambda image:ImageDraw.Draw(image).rectangle((740,305,759,324),fill=(127,127,127)))

    def nearby(image):
        ImageDraw.Draw(image).rectangle((687,350,706,379),fill=(127,127,127))
    test('independent_patch_one_background_pixel_away',nearby)
    test('seam_is_actual_background',lambda image:image.paste(hidden.crop((595,339,686,340)),(595,339)))
    test('seam_is_two_background_pixels',lambda image:image.paste(hidden.crop((595,339,686,341)),(595,339)))
    test('seam_is_unrelated_magenta',lambda image:ImageDraw.Draw(image).line((595,339,685,339),fill=(255,0,255)))

    assert all(row['candidate_passed']==row['expected_passed'] for row in rows),[(row['name'],row['candidate_passed']) for row in rows]
    assert source.read_bytes()==source_raw
    assert all(sha(Path(path).read_bytes())==expected for path,expected in originals.items())
    report={'schema':1,'passed':True,'actual_raw_positive_cases':3,'synthetic_negative_cases':len(rows)-3,
        'rows':rows,'candidate_extractor_sha256':sha((WORK/'candidate_extractor.py').read_bytes()),
        'controls_sha256':sha(Path(__file__).read_bytes()),'original_analyzer_sha256':sha(Path(original.__file__).read_bytes()),
        'original_inputs_sha256':originals,'original_inputs_unchanged':True,
        'fixed_original_vertical_fov':fov,'new_fov_search_or_fit_performed':False,
        'original_color_tests_unchanged':True,'original_final_metric_thresholds_unchanged':True,
        'expected_silhouette_used_to_build_mask':False,
        'scope':'Actual old raw extraction replay with original fixed FOV and original metric gates; diagnostic candidate only',
        'limitations':['A separately rendered object with identical color and identical one-pixel foreground/background raster cannot be distinguished from the same stone using pixels alone.',
            'Uniform scaling across all calibration views is mathematically confounded with camera FOV; the scaling negative perturbs one tilted view against the original fixed common FOV.',
            'Candidate has not been run in a new live MC calibration or used as a release qualification source.'],
        'MC_started':False,'RPC_dispatched':False,'formal_A_accepted':False,'world_A_accepted':False,'manual_closures_added':0}
    with (out/'report.json').open('x',encoding='ascii') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({'passed':True,'positive_cases':3,'negative_cases':len(rows)-3,
        'report_sha256':sha((out/'report.json').read_bytes()),
        'actual_tilted_fit':rows[2]['fit'],'bridged_pixels':len(rows[2]['extractor_observations']['bridged_pixels'])}))


if __name__=='__main__':
    main()
