"""Native billboard carriers for the existing GPU stars (no CPU star loop)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'resource_pack'


def write(path, value):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')


def generate():
    materials = {'version': '1.0.0'}
    for kind, count in (('survey', 971), ('strike', 328), ('aura', 176)):
        name = 'modern_projection_' + kind + '_native_glow'
        shader = 'aura' if kind == 'aura' else 'survey_stars'
        defines = ['NATIVE_GLOW', 'AURA_GLOW' if kind == 'aura' else 'SURVEY_GLOW']
        if kind == 'strike':
            defines.append('SURVEY_STRIKE')
        materials[name + ':particles_base'] = {
            'vertexShader': 'shaders/glsl/modern_projection_' + shader + '.vertex',
            'fragmentShader': 'shaders/glsl/modern_projection_' + shader + '.fragment',
            '+defines': defines,
            '+states': ['Blending', 'DisableDepthWrite', 'DisableCulling'],
            'blendSrc': 'SourceAlpha', 'blendDst': 'One',
            'vertexFields': [{'field': field} for field in ('Position', 'Color', 'UV0')]}
        index = '(v.particle_lifetime-1048576)'
        if kind == 'aura':
            ux, uy, red = 'v.ux+' + index, 'v.uy', 'v.red'
            radius = 3
        else:
            ux = 'v.ux+math.mod(math.floor(' + index + '/256),2)*8192'
            uy = 'v.uy+math.mod(' + index + ',256)*64'
            red = 'v.red+math.floor(' + index + '/512)*128'
            radius = (4 if kind == 'strike' else
                      'math.sqrt(math.pow(math.mod(v.ux,64)+1,2)'
                      '+math.pow(math.floor(v.ux/64)+1,2)'
                      '+math.pow(v.uy+1,2))*0.5+18')
        # Large visible carriers produced stray quads in the native renderer.
        # One extra, shader-hidden particle keeps the emitter's conservative
        # bounds, including a 64x128x64 box whose centre is outside the view.
        # Visible particles use tiny carriers; the sentinel never enters the
        # trajectory shader. Its compact ID is exactly the visible count.
        carrier_size = index + '<' + str(count) + '?0.000001:(' + str(radius) + ')'
        # Match the UNORM16 denominator: a 65535-wide virtual texture with
        # corners (.5,3) survives float32 rounding/truncation and up to .5
        # texel atlas inset while leaving 14 static payload bits. The last
        # upper corner is exactly 65535, so UVs never exceed one.
        # No continuously changing value is packed into these UV addresses.
        components = {
            'minecraft:emitter_initialization': {
                'creation_expression': 'v.counter=0;v.ready=0;v.ux=0;v.uy=0;'
                                       'v.red=0;v.green=0;v.blue=0;v.alpha=0;'},
            'minecraft:emitter_rate_instant': {'num_particles': count + 1},
            'minecraft:emitter_lifetime_once': {'active_time': 1048576},
            'minecraft:emitter_local_space': {'position': True, 'rotation': False},
            'minecraft:emitter_shape_point': {'direction': [0, 0, 0]},
            'minecraft:particle_initial_speed': 0,
            # Molang variables are emitter-shared in this client. Store the
            # stable per-particle address in its long, individual lifetime.
            'minecraft:particle_lifetime_expression': {
                'max_lifetime': 'v.counter=v.counter+1;return 1048576+v.counter-1;'},
            'minecraft:particle_motion_parametric': {'relative_position': [0, 0, 0]},
            'minecraft:particle_appearance_billboard': {
                'size': [carrier_size, carrier_size], 'facing_camera_mode': 'rotate_xyz',
                'uv': {'texture_width': 65535, 'texture_height': 65535,
                       'uv': ['(' + value + ')*4+0.5' for value in (ux, uy)],
                       'uv_size': [2.5, 2.5]}},
            'minecraft:particle_appearance_tinting': {
                # Preserve metadata (especially sentinel ID bits) while
                # hidden. Alpha zero alone gates registration and cleanup.
                'color': ['(' + value + ')/255' for value in (red, 'v.green', 'v.blue')]
                         + ['v.ready?v.alpha/255:0']}}
        write('particles/modern_projection_' + kind + '_glow.json', {
            'format_version': '1.10.0', 'particle_effect': {
                'description': {'identifier': 'modern_projection:' + kind + '_glow',
                                'basic_render_parameters': {'material': name,
                                    'texture': 'textures/modern_projection/glow_carrier'}},
                'components': components}})
    write('materials/particles.material', {'materials': materials})


if __name__ == '__main__':
    generate()
