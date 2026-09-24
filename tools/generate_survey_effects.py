"""Generate bounded GPU particle meshes; no per-particle Python runtime work."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'resource_pack'


def write(path, data):
    (ROOT / path).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf8')


def geometry(name, cubes):
    write('models/entity/modern_projection_' + name + '.geo.json', {
        'format_version':'1.12.0', 'minecraft:geometry':[{
            'description':{'identifier':'geometry.modern_projection.' + name,
                'texture_width':2,'texture_height':2,'visible_bounds_width':140,
                'visible_bounds_height':140,'visible_bounds_offset':[0,0,0]},
            'bones':[{'name':'root','pivot':[0,0,0],'cubes':cubes}]}]})


def generate():
    for name, count in [('survey_wire',576),('survey_guide',576),
                        ('survey_stars',2560),('survey_strike',512)]:
        # POSITION encodes a primitive address and its four vertices. The
        # shader turns these into short comet trails, eight triangular
        # faces per tumbling crystal, and a small number of star billboards.
        # Keep encoded coordinates below 256 so mobile mediump POSITION
        # retains the half-unit quad corners without precision loss.
        geometry(name,[{'origin':[(i%64)*4-.5,(i//64)*4-.5,0],'size':[1,1,0],
            'uv':{'north':{'uv':[0,0],'uv_size':[2,2]}}} for i in range(count)])
    for name in ('survey_wire','survey_guide','survey_stars','survey_strike'):
        behavior = json.loads((ROOT.parent / 'behavior_pack/entities/modern_projection_outline.json').read_text())
        behavior['minecraft:entity']['description']['identifier'] = 'modern_projection:' + name
        (ROOT.parent / ('behavior_pack/entities/modern_projection_' + name + '.json')).write_text(
            json.dumps(behavior,indent=2)+'\n',encoding='utf8')
        write('entity/modern_projection_' + name + '.entity.json', {
            'format_version':'1.10.0','minecraft:client_entity':{'description':{
                'identifier':'modern_projection:' + name,
                'materials':{'default':'modern_projection_' + name},
                'textures':{'default':'textures/modern_projection/transparent'},
                'geometry':{'default':'geometry.modern_projection.outline' if name == 'survey_wire'
                            else 'geometry.modern_projection.' + name},
                'render_controllers':['controller.render.modern_projection.anchor']}}})


if __name__ == '__main__':
    generate()
