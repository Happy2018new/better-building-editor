"""Diagnose native water in three geometry paths of one public wet blueprint.

Run through run_live_check.py. This retains the original world, camera, ROI,
pixel thresholds and cleanup of verify_wet_actor_visuals. A positive water
control is reported separately from actor acceptance; failed controls remain
failed. No production renderer or logical fixture cells are changed.
"""
import verify_wet_actor_visuals as wet


MODES = ('raw', 'prepared', 'context')
SOURCE_CASE = 'sign_adjacent_water'
SOURCE = wet.CASES[SOURCE_CASE]

INSTALL_PATH = '''assert not hasattr(sys,'_liquid_path_geometry_saved')
sys._liquid_path_geometry_saved=b.geometry
sys._liquid_path_context_saved=dict(b.context_models)
b.context_models.clear()
sys._liquid_path_mode=%r
def liquid_path_geometry(document,visible=None,name=None,context_document=None,prepared=None):
 original=sys._liquid_path_geometry_saved
 if prepared is not None and '_context_batches' not in prepared:
  return original(document,visible,name,context_document,prepared)
 mode=sys._liquid_path_mode
 if mode=='raw':
  return original(document,visible,name,prepared=document.palette_data(visible))
 if mode=='prepared':
  return original(document,visible,name)
 return original(document,visible,name,context_document,prepared)
b.geometry=liquid_path_geometry
_result=json.dumps({'mode':sys._liquid_path_mode,'fixture':'test.entities.signs',
 'case':'adjacent_water','logical_cells_unchanged':True})
'''

RESTORE_PATH = '''if hasattr(sys,'_liquid_path_geometry_saved'):
 b.stop_projection()
 b.geometry=sys._liquid_path_geometry_saved
 b.context_models.clear()
 b.context_models.update(sys._liquid_path_context_saved)
 del sys._liquid_path_geometry_saved
 del sys._liquid_path_mode
 del sys._liquid_path_context_saved
_result=True
'''


def probe_case(check, mode, args, row):
    row['geometry_path'] = mode
    row['public_case'] = SOURCE_CASE
    saved_crop = wet.CROP
    wet.CROP = saved_crop.replace('b.project()', INSTALL_PATH % mode + '\nb.project()')
    try:
        return wet.wet_case(check, mode, args, row)
    finally:
        wet.CROP = saved_crop
        row['geometry_path_restored'] = check.run(RESTORE_PATH)


_write = wet.write_report


def write_report(path, report):
    report['diagnostic'] = True
    report['geometry_paths'] = MODES
    report['water_controls'] = {
        row['geometry_path']: {
            view: frames.get('components', {}).get('water')
            for view, frames in row.get('views', {}).items()
        } for row in report['cases']
    }
    _write(path, report)
    report['scope'] = ('Public sign adjacent-water fixture: unchanged raw palette, '
                       'prepared palette, and production context geometry; '
                       'separate native water positive controls')
    wet._save(path, report)


def configure():
    wet.CASES = dict((mode, SOURCE) for mode in MODES)
    wet.world.CASES = MODES
    wet.world.world_case = probe_case
    wet.world.write_json = write_report


if __name__ == '__main__':
    configure()
    raise SystemExit(wet.world.main())
