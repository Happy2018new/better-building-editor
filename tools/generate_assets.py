"""Rebuild local smooth typography, icons and native JsonUI skins with Pillow."""
import argparse
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'behavior_pack/HelloScript/projection'
OUT = ROOT / 'resource_pack/textures/modern_projection'


def sprites(font_path):
    from generate_phrase_atlas import build
    build(font_path)


def shape(name, size, draw):
    img = Image.new('RGBA', (size[0] * 3, size[1] * 3))
    draw(ImageDraw.Draw(img), 3)
    img.resize(size, Image.Resampling.LANCZOS).save(OUT / (name + '.png'))


def graphics():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'icons').mkdir(exist_ok=True)
    biome_icons()
    shape('rounded', (64, 64), lambda d, s: d.rounded_rectangle((0, 0, 64*s-1, 64*s-1), 24*s, fill='white'))
    # Bilinear sampling must not blend transparent black into the tinted edge.
    # Keep a white RGB matte even in fully transparent texels of this alpha mask.
    alpha = Image.open(OUT / 'rounded.png').getchannel('A')
    rounded = Image.new('RGBA', alpha.size, 'white')
    rounded.putalpha(alpha)
    rounded.save(OUT / 'rounded.png')
    shape('dot', (16, 16), lambda d, s: d.ellipse((1*s, 1*s, 15*s, 15*s), fill='white'))
    shape('scroll_thumb', (12, 72), lambda d, s: d.rounded_rectangle((0, 0, 12*s-1, 72*s-1), 6*s, fill='white'))
    shape('knob', (36, 36), lambda d, s: (d.ellipse((2*s, 3*s, 34*s, 35*s), fill='#CCD8EE'),
        d.ellipse((3*s, 2*s, 33*s, 32*s), fill='white'), d.ellipse((13*s, 12*s, 23*s, 22*s), fill='#477AF4')))
    Image.new('RGBA', (2, 2)).save(OUT / 'transparent.png')
    flecks = Image.new('RGBA', (448, 448))
    for i in range(16):
        progress = i / 15.
        particle = Image.new('RGBA', (336, 336))
        draw = ImageDraw.Draw(particle)
        spread = 1 - (1 - progress) ** 3
        alpha = int(215 * (1 - progress) ** 1.15)
        # Six distinct, slightly asymmetric flecks. No enclosing ring or flash.
        for j, angle in enumerate((.18, 1.34, 2.48, 3.51, 4.63, 5.62)):
            distance = 5 + (16 if j % 2 else 20) * spread
            length = (2.6 if j % 2 else 1.5) * (1 - .65 * progress)
            points = [(168 + math.cos(angle) * d * 6, 168 + math.sin(angle) * d * 6)
                      for d in (distance, distance + length)]
            draw.line(points, fill=(69, 121, 220, alpha), width=8)
            for x, y in points:
                draw.ellipse((x-4, y-4, x+4, y+4), fill=(69, 121, 220, alpha))
        flecks.paste(particle.resize((112, 112), Image.Resampling.LANCZOS), ((i % 4) * 112, (i // 4) * 112))
    flecks.save(OUT / 'click_flecks.png')
    for name, color in [('input_bg', '#F0F4FA'), ('input_hover', '#E6EDFA')]:
        shape(name, (32, 32), lambda d, s, c=color: d.rounded_rectangle((0, 0, 32*s-1, 32*s-1), 6*s, fill=c))
    grid = Image.new('RGBA', (800, 800), '#F7F9FC')
    d = ImageDraw.Draw(grid)
    for x in range(0, 800, 24):
        for y in range(0, 800, 24):
            d.ellipse((x, y, x+1, y+1), fill='#C7D3E2')
    grid.save(OUT / 'viewport_grid.png')
    paths = {
        'plus': [[(12,4),(12,20)],[(4,12),(20,12)]],
        'search': [[(15,15),(22,22)],[(17,10),(16,5),(11,2),(6,3),(2,7),(2,12),(6,17),(12,18),(17,14),(17,10)]],
        'minus': [[(4,12),(20,12)]],
        'close': [[(6,6),(18,18)],[(18,6),(6,18)]],
        'cube': [[(12,2),(22,7),(22,17),(12,22),(2,17),(2,7),(12,2)],[(2,7),(12,12),(22,7)],[(12,12),(12,22)]],
        'cursor': [[(4,2),(4,20),(9,15),(13,22),(17,20),(13,13),(21,13),(4,2)]],
        'brush': [[(6,15),(16,3),(21,8),(10,19),(6,15)],[(6,15),(3,17),(3,22),(8,21),(10,19)]],
        'move': [[(12,2),(12,22)],[(2,12),(22,12)],[(8,6),(12,2),(16,6)],[(8,18),(12,22),(16,18)],[(6,8),(2,12),(6,16)],[(18,8),(22,12),(18,16)]],
        'grid': [[(3,3),(21,3),(21,21),(3,21),(3,3)],[(9,3),(9,21)],[(15,3),(15,21)],[(3,9),(21,9)],[(3,15),(21,15)]],
        'spark': [[(12,2),(15,9),(22,12),(15,15),(12,22),(9,15),(2,12),(9,9),(12,2)]],
        'save': [[(3,3),(17,3),(21,7),(21,21),(3,21),(3,3)],[(7,3),(7,9),(16,9),(16,3)],[(7,21),(7,14),(17,14),(17,21)]],
        'undo': [[(7,4),(3,8),(7,12)],[(3,8),(14,8),(19,11),(20,15),(18,19),(13,20)]],
        'redo': [[(17,4),(21,8),(17,12)],[(21,8),(10,8),(5,11),(4,15),(6,19),(11,20)]],
        'eye': [[(2,12),(6,7),(12,5),(18,7),(22,12),(18,17),(12,19),(6,17),(2,12)],[(12,9),(15,12),(12,15),(9,12),(12,9)]],
        'lock': [[(5,10),(19,10),(19,21),(5,21),(5,10)],[(8,10),(8,6),(10,3),(14,3),(16,6),(16,10)],[(12,14),(12,17)]],
        'unlock': [[(5,10),(19,10),(19,21),(5,21),(5,10)],[(8,10),(8,6),(10,3),(15,3),(18,6)],[(12,14),(12,17)]],
        'home': [[(2,11),(12,2),(22,11)],[(5,9),(5,22),(10,22),(10,15),(15,15),(15,22),(19,22),(19,9)]],
        'orbit': [[(4,8),(7,4),(12,2),(18,4),(21,9),(21,15),(18,20),(11,22),(5,19),(3,14)],[(3,4),(4,8),(9,8)],[(6,12),(12,16),(19,12)]],
        'play': [[(7,3),(21,12),(7,21),(7,3)]],
        'pin': [[(12,22),(5,13),(4,8),(7,3),(12,2),(18,4),(20,9),(18,14),(12,22)],[(12,7),(15,10),(12,13),(9,10),(12,7)]],
        'library': [[(3,3),(8,3),(8,21),(3,21),(3,3)],[(11,3),(16,3),(16,21),(11,21),(11,3)],[(18,4),(23,20)]],
        'projection': [[(12,2),(21,7),(21,16),(12,21),(3,16),(3,7),(12,2)],[(3,7),(12,12),(21,7)],[(12,12),(12,21)],[(1,22),(23,22)]],
        'check': [[(3,12),(9,18),(21,5)]],
        'info': [[(12,9),(12,17)],[(12,5),(12,6)],[(12,2),(19,5),(22,12),(19,19),(12,22),(5,19),(2,12),(5,5),(12,2)]],
        'draft': [[(5,2),(15,2),(20,7),(20,22),(5,22),(5,2)],[(15,2),(15,7),(20,7)],[(8,12),(16,12)],[(8,16),(14,16)]],
        'select_all': [[(8,3),(3,3),(3,8)],[(16,3),(21,3),(21,8)],[(3,16),(3,21),(8,21)],[(16,21),(21,21),(21,16)],[(7,7),(17,7),(17,17),(7,17),(7,7)]],
        'box_outline': [[(4,4),(9,4)],[(15,4),(20,4),(20,9)],[(20,15),(20,20),(15,20)],[(9,20),(4,20),(4,15)],[(4,9),(4,4)]],
        'select_box': [[(8,3),(3,3),(3,8)],[(16,3),(21,3),(21,8)],[(3,16),(3,21),(8,21)],[(16,21),(21,21),(21,16)]],
        'layers': [[(2,8),(12,3),(22,8),(12,13),(2,8)],[(2,13),(12,18),(22,13)],[(2,18),(12,23),(22,18)]],
        'invert': [[(3,3),(21,3),(21,21),(3,21),(3,3)],[(12,3),(12,21)],[(3,12),(21,12)],[(5,5),(10,10)],[(14,14),(19,19)]],
        'expand': [[(8,3),(3,3),(3,8)],[(3,3),(9,9)],[(16,3),(21,3),(21,8)],[(21,3),(15,9)],[(3,16),(3,21),(8,21)],[(3,21),(9,15)],[(16,21),(21,21),(21,16)],[(21,21),(15,15)]],
        'contract': [[(3,3),(9,9)],[(9,4),(9,9),(4,9)],[(21,3),(15,9)],[(15,4),(15,9),(20,9)],[(3,21),(9,15)],[(4,15),(9,15),(9,20)],[(21,21),(15,15)],[(15,20),(15,15),(20,15)]],
        'surface': [[(2,8),(12,3),(22,8),(12,13),(2,8)],[(2,8),(2,18),(12,23),(22,18),(22,8)],[(12,13),(12,23)],[(8,8),(12,6),(16,8)]],
        'pick': [[(16,2),(22,8)],[(14,4),(20,10)],[(15,7),(4,18),(3,22),(7,21),(18,10)]],
        'fill': [[(10,3),(20,13),(12,21),(3,12),(11,4)],[(3,12),(20,12)],[(8,1),(13,6)],[(21,15),(19,19),(21,22),(23,19),(21,15)]],
        'erase': [[(3,14),(14,3),(22,11),(11,22),(6,22),(3,19),(3,14)],[(8,9),(17,18)],[(11,22),(22,22)]],
        'replace': [[(3,7),(21,7)],[(17,3),(21,7),(17,11)],[(21,17),(3,17)],[(7,13),(3,17),(7,21)]],
        'copy': [[(8,8),(21,8),(21,21),(8,21),(8,8)],[(4,16),(3,16),(3,3),(16,3),(16,4)]],
        'cut': [[(5,2),(15.5,15.5)],[(19,2),(8.5,15.5)]],
        'paste': [[(8,5),(4,5),(4,22),(20,22),(20,5),(16,5)],[(8,3),(16,3),(16,7),(8,7),(8,3)],[(8,12),(16,12)],[(8,16),(14,16)]],
        'drop': [[(12,2),(5,11),(4,16),(7,21),(12,23),(17,21),(20,16),(19,11),(12,2)],[(8,15),(9,18),(12,19)]],
        'rotate_left': [[(3,9),(6,4),(12,2),(18,4),(21,9),(21,15),(18,20),(12,22)],[(3,3),(3,9),(9,9)]],
        'rotate_right': [[(21,9),(18,4),(12,2),(6,4),(3,9),(3,15),(6,20),(12,22)],[(21,3),(21,9),(15,9)]],
        'mirror_x': [[(12,2),(12,22)],[(8,6),(3,12),(8,18),(8,6)],[(16,6),(21,12),(16,18),(16,6)]],
        'mirror_y': [[(2,12),(22,12)],[(6,8),(12,3),(18,8),(6,8)],[(6,16),(12,21),(18,16),(6,16)]],
        'arrow_right': [[(3,12),(21,12)],[(14,5),(21,12),(14,19)]],
        'arrow_left': [[(21,12),(3,12)],[(10,5),(3,12),(10,19)]],
        'arrow_up': [[(12,21),(12,3)],[(5,10),(12,3),(19,10)]],
        'arrow_down': [[(12,3),(12,21)],[(5,14),(12,21),(19,14)]],
        'array': [[(2,7),(10,7),(10,17),(2,17),(2,7)],[(14,7),(22,7),(22,17),(14,17),(14,7)]],
        'walls': [[(3,20),(3,4),(12,8),(21,4),(21,20)],[(3,14),(12,18),(21,14)],[(12,8),(12,18)]],
        'sphere': [[(12,2),(19,5),(22,12),(19,19),(12,22),(5,19),(2,12),(5,5),(12,2)],[(12,2),(8,8),(8,16),(12,22),(16,16),(16,8),(12,2)],[(2,12),(22,12)]],
        'cylinder': [[(3,6),(6,3),(18,3),(21,6),(18,9),(6,9),(3,6),(3,19),(6,22),(18,22),(21,19),(21,6)]],
        'pyramid': [[(12,2),(2,20),(12,23),(22,20),(12,2),(12,23)]],
        'dome': [[(2,20),(3,11),(7,4),(12,2),(17,4),(21,11),(22,20),(2,20)],[(12,2),(9,11),(9,20)],[(12,2),(15,11),(15,20)]],
        'arch': [[(3,22),(3,10),(5,5),(9,2),(15,2),(19,5),(21,10),(21,22),(16,22),(16,11),(14,8),(10,8),(8,11),(8,22),(3,22)]],
        'stairs': [[(2,21),(2,16),(8,16),(8,10),(14,10),(14,4),(21,4),(21,21),(2,21)]],
        'line': [[(4,20),(20,4)],[(2,18),(6,18),(6,22),(2,22),(2,18)],[(18,2),(22,2),(22,6),(18,6),(18,2)]],
        'floor': [[(2,13),(14,5),(23,11),(11,20),(2,13)],[(7,10),(17,16)],[(8,17),(19,8)]],
        'roof': [[(2,14),(12,3),(22,14)],[(5,14),(12,7),(19,14)],[(5,14),(5,22),(19,22),(19,14)]],
        'stripes_x': [[(4,3),(4,21)],[(12,3),(12,21)],[(20,3),(20,21)]],
        'stripes_y': [[(3,4),(21,4)],[(3,12),(21,12)],[(3,20),(21,20)]],
        'stripes_z': [[(2,12),(12,2)],[(2,22),(22,2)],[(12,22),(22,12)]],
        'noise': [[(4,3),(4,6)],[(12,9),(12,12)],[(20,2),(20,5)],[(3,17),(3,20)],[(20,16),(20,19)],[(11,21),(11,23)]],
        'gradient': [[(10,3),(14,3)],[(7,9),(17,9)],[(4,15),(20,15)],[(2,21),(22,21)]],
        'brick': [[(2,4),(22,4),(22,20),(2,20),(2,4)],[(2,12),(22,12)],[(8,4),(8,12)],[(16,12),(16,20)]],
        'repair': [[(3,3),(21,3),(21,21),(3,21),(3,3)],[(7,12),(17,12)],[(12,7),(12,17)]],
        'gravity': [[(12,2),(12,16)],[(6,10),(12,16),(18,10)],[(3,21),(21,21)]],
        'foundation': [[(4,2),(20,2),(20,7),(4,7),(4,2)],[(12,10),(12,19)],[(8,15),(12,19),(16,15)],[(3,23),(21,23)]],
        'sliders': [[(3,6),(21,6)],[(3,12),(21,12)],[(3,18),(21,18)],[(8,3),(8,9)],[(16,9),(16,15)],[(9,15),(9,21)]],
        'history': [[(3,10),(5,5),(10,2),(16,3),(21,8),(22,14),(18,20),(12,22),(6,20)],[(3,3),(3,10),(9,10)],[(12,6),(12,13),(17,16)]],
        'top_view': [[(3,7),(21,7),(21,22),(3,22),(3,7)],[(12,1),(12,13)],[(8,9),(12,13),(16,9)]],
        'front_view': [[(3,3),(21,3),(21,21),(3,21),(3,3)],[(7,12),(17,12)],[(13,8),(17,12),(13,16)]],
        'folder': [[(2,20),(2,5),(10,5),(13,8),(22,8),(22,20),(2,20)]],
        'edit': [[(4,16),(16,4),(21,9),(9,21),(3,22),(4,16)],[(13,7),(18,12)]],
        'trash': [[(3,5),(21,5)],[(8,5),(8,2),(16,2),(16,5)],[(5,5),(6,22),(18,22),(19,5)],[(10,9),(10,18)],[(14,9),(14,18)]],
        'motion': [[(2,7),(9,7)],[(2,12),(6,12)],[(2,17),(9,17)],[(12,4),(21,12),(12,20),(12,4)]],
    }
    for name, strokes in paths.items():
        img = Image.new('RGBA', (96,96))
        d = ImageDraw.Draw(img)
        for stroke in strokes:
            d.line([(x*4,y*4) for x,y in stroke], fill='white', width=7, joint='curve')
        if name == 'cut':
            for cx in (6, 18):
                d.ellipse(((cx-3.5)*4,14.5*4,(cx+3.5)*4,21.5*4), outline='white', width=7)
        img.resize((48,48),Image.Resampling.LANCZOS).save(OUT / 'icons' / (name+'.png'))
    logo = Image.new('RGBA', (128,128))
    d = ImageDraw.Draw(logo)
    d.rounded_rectangle((0,0,127,127),32,fill='#477AF4')
    d.polygon([(64,24),(103,45),(103,84),(64,105),(25,84),(25,45)], fill='#DDE8FF')
    d.polygon([(64,66),(103,45),(103,84),(64,105)], fill='#92B3FF')
    d.line([(25,45),(64,66),(103,45)],fill='white',width=3)
    d.line([(64,66),(64,105)],fill='white',width=3)
    logo.save(OUT/'logo.png')
    axes=Image.new('RGBA',(150,150)); d=ImageDraw.Draw(axes)
    for end,color in [((125,105),'#EF8690'),((28,108),'#6E9AF1'),((76,22),'#60B9A0')]:
        d.line([(76,78),end],fill=color,width=4); x,y=end; d.ellipse((x-7,y-7,x+7,y+7),fill=color)
    d.ellipse((70,72,82,84),fill='#8394AC'); axes.save(OUT/'axes.png')


def biome_icons():
    """Distinct biome silhouettes, using the existing 24-unit line icon style."""
    paths = {
        'plains': [[(2,21),(22,21)],[(8,21),(7,14),(4,10)],[(8,21),(10,12),(13,8)],
                   [(15,21),(14,14),(12,12)],[(15,21),(18,12),(21,11)]],
        'forest': [[(8,16),(3,16),(2,12),(4,9),(4,6),(8,3),(12,6),(12,9),(14,12),(13,16),(8,16)],
                   [(8,13),(8,22)],[(15,7),(18,5),(21,8),(21,11),(23,14),(22,17),(17,17)],[(18,15),(18,22)]],
        'birch_forest': [[(9,22),(9,4),(15,4),(15,22)],[(9,9),(12,9)],[(12,14),(15,14)],
                         [(9,19),(12,19)],[(9,6),(5,3)],[(15,10),(19,6)],[(6,22),(18,22)]],
        'taiga': [[(12,2),(5,10),(8,10),(3,16),(10,16),(10,22),(14,22),(14,16),(21,16),(16,10),(19,10),(12,2)]],
        'swampland': [[(2,18),(6,20),(10,18),(14,20),(18,18),(22,20)],[(3,23),(7,21),(11,23)],
                      [(9,17),(9,6)],[(8,4),(10,4),(10,11),(8,11),(8,4)],
                      [(16,17),(16,9),(20,6)],[(5,16),(5,12)]],
        'mangrove_swamp': [[(5,11),(2,9),(3,5),(7,4),(10,2),(15,3),(17,5),(21,5),(22,9),(19,11),(5,11)],
                           [(12,11),(12,16),(5,22)],[(12,16),(19,22)],[(8,12),(7,18),(2,21)],
                           [(17,12),(18,17),(22,20)],[(12,16),(12,22)]],
        'jungle': [[(12,22),(12,8)],[(12,8),(7,4),(3,5),(1,9),(7,8),(12,8)],
                   [(12,8),(16,3),(20,3),(23,7),(17,7),(12,8)],
                   [(12,8),(6,11),(4,16)],[(12,8),(18,11),(20,16)],[(7,22),(17,22)]],
        'desert': [[(10,21),(10,4),(12,2),(14,4),(14,21)],
                   [(10,14),(5,14),(3,12),(3,7),(6,7),(6,11),(10,11)],
                   [(14,17),(19,17),(21,15),(21,10),(18,10),(18,14),(14,14)],[(3,22),(21,22)]],
        'savanna': [[(2,10),(5,6),(9,6),(12,3),(18,4),(22,8),(22,10),(2,10)],
                    [(7,10),(12,15),(17,10)],[(12,15),(12,22)],[(3,22),(21,22)]],
        'ice_plains': [[(12,2),(12,22)],[(3,7),(21,17)],[(3,17),(21,7)],
                       [(8,4),(12,8),(16,4)],[(8,20),(12,16),(16,20)],
                       [(3,11),(7,9),(7,5)],[(17,19),(17,15),(21,13)],
                       [(3,13),(7,15),(7,19)],[(17,5),(17,9),(21,11)]],
    }
    directory = OUT / 'icons'
    directory.mkdir(parents=True, exist_ok=True)
    for name, strokes in paths.items():
        img = Image.new('RGBA', (96,96))
        draw = ImageDraw.Draw(img)
        for stroke in strokes:
            draw.line([(x*4,y*4) for x,y in stroke], fill='white', width=7, joint='curve')
        img.resize((48,48), Image.Resampling.LANCZOS).save(directory / ('biome_'+name+'.png'))


def native_input_controls():
    # The engine resolves these native names even when the placeholder is empty.
    # Keep the original edit/placeholder tree; focus only changes its appearance.
    label_geometry={'layer':1,'size':['default','default'],'min_size':['100% - 6px',0],
                    'offset':[-3,0],'anchor_from':'right_middle','anchor_to':'right_middle'}
    # Only the display label uses its locked color to select the focused ink.
    # Its parent edit_box remains enabled and owns input, cursor, IME and focus.
    label=dict(label_geometry, locked_color=[.95,.96,.98], locked_alpha=1., bindings=[
        {'binding_type':'$text_edit_box_content_binding_type',
         'binding_condition':'$text_edit_box_binding_condition',
         'binding_collection_name':'$text_edit_box_grid_collection_name',
         'binding_name':'$text_edit_box_content_binding_name','binding_name_override':'#item_name'},
        {'binding_type':'$text_color_binding_type','binding_name':'$text_color_binding_name','binding_name_override':'#color'},
        {'binding_name':'#newline_refresh'},
        {'binding_type':'view','source_property_name':'(not #text_edit_selected)','target_property_name':'#enabled'}])
    return [
        {'centering_panel':{'type':'panel','size':['100%','100% - 4px'],'controls':[
            {'clipper_panel':{'type':'panel','size':'$text_edit_clipping_panel_size',
                'anchor_from':'left_middle','anchor_to':'left_middle','clips_children':True,'controls':[
                {'display_text@common.text_edit_box_label':label},
                {'visibility_panel':{'type':'panel','controls':[
                    {'place_holder_control@common.text_edit_box_place_holder_label':dict(label_geometry)}],
                    'bindings':[{'binding_type':'view','source_control_name':'display_text',
                        'source_property_name':"(#item_name = '')",'target_property_name':'#visible','resolve_sibling_scope':True}]}},
                {'active_background':{'type':'panel','layer':0,'visible':False,'size':['100%','100%'],
                    # Native geometry survives UpdateScreen/child removal. The
                    # former Python-sized zero-size template patches did not.
                    'controls':[
                        {'p%d' % (r*3+c):{'type':'image','texture':'textures/modern_projection/rounded',
                            'bilinear':True,'keep_ratio':False,'layer':0,'color':[.25,.27,.30],
                            'anchor_from':('top','center','bottom')[r]+'_'+('left','middle','right')[c]
                                if r!=1 else ('left_middle','center','right_middle')[c],
                            'anchor_to':('top','center','bottom')[r]+'_'+('left','middle','right')[c]
                                if r!=1 else ('left_middle','center','right_middle')[c],
                            'size':['100% - 4px' if c==1 else 2,'100% - 4px' if r==1 else 2],
                            'uv':[u,v],'uv_size':[16 if c==1 else 24,16 if r==1 else 24]}}
                        for r,v in enumerate((0,24,40)) for c,u in enumerate((0,24,40))],
                    'bindings':[{'binding_type':'view','source_control_name':'display_text',
                        'resolve_sibling_scope':True,'source_property_name':'#text_edit_selected','target_property_name':'#visible'}]}}
            ]}}
        ]}},
        {'default@ModernProjection.invisible':{}}, {'hover@ModernProjection.invisible':{}},
        {'pressed@ModernProjection.invisible':{}}, {'locked@ModernProjection.invisible':{}}
    ]


def native_skin():
    # Based on the documented common slider structure; our visual track is Pyreact.
    ns='ModernProjection'; tex='textures/modern_projection/'
    skin={'namespace':ns,
        'label@PyreactBase.label':{'font_type':'smooth','backup_font_type':'smooth'},
        'motion_group@PyreactBase.panel':{'type':'image','texture':'','propagate_alpha':True},
        'type_image@PyreactBase.image':{'bilinear':True},
        'inventory_modal@PyreactBase.panel':{'type':'input_panel','modal':True,'inline_modal':True,'focus_enabled':False},
        'pointer@PyreactBase.button':{'button_mappings':[],'is_handle_button_move_event':True},
        'doll@PyreactBase.paperDoll':{'rotation':'none', 'enable_scissor_test':True},
        'click_observer@PyreactBase.panel': {'type': 'input_panel',
            'consume_hover_events': False,
            'button_mappings': [{'from_button_id': 'button.menu_select',
                'to_button_id': '#modern_projection_pointer_down', 'mapping_type': 'global', 'consume_event': False}]},
        'round@PyreactBase.panel': {'$mp_patch_layer|default':2, 'controls': [
            {'p%d' % (r * 3 + c): {'type': 'image', 'texture': tex + 'rounded', 'bilinear': True,
                'anchor_from': 'top_left', 'anchor_to': 'top_left', 'keep_ratio': False, 'layer': '$mp_patch_layer',
                'uv': [u, v], 'uv_size': [16 if c == 1 else 24, 16 if r == 1 else 24],
                'size': [0, 0]}}
            for r, v in enumerate((0, 24, 40)) for c, u in enumerate((0, 24, 40))]},
        'input_background':{'type':'image','texture':tex+'input_bg','size':['100%','100%'],'keep_ratio':False,'nineslice_size':[4,4,4,4],'bilinear':True},
        'input_hover@ModernProjection.input_background':{'texture':tex+'input_hover'},
        'input@PyreactBase.input':{'$text_background_default':ns+'.invisible', '$text_background_hover':ns+'.invisible',
            '$edit_box_default_texture':tex+'transparent', '$edit_box_hover_texture':tex+'transparent', '$font_scale_factor':1.,
            # Native settings-form font, sized for this editor's compact layout.
            # Undo common.text_edit_box's 4px vertical inset.
            # Keep horizontal clipping/caret scrolling inside the padded field.
            '$text_edit_clipping_panel_size':['100%', '100% + 4px'],
            # Retain all required native names, including place_holder_control.
            '$place_holder_text':'', '$text_box_text_color':[.07,.12,.20],
            'controls':native_input_controls()},
        'invisible':{'type':'image','texture':tex+'transparent','size':['100%','100%'],'alpha':0},
        'scroll_thumb':{'type':'image','texture':'textures/ui/white','size':[2,'100%'],
                        'color':[.65,.73,.85],'layer':4},
        'scroll@PyreactBase.scrollBase':{'$scroll_size':[3,'100%'],'$scroll_track_image_control':'common.empty_panel',
            '$scroll_box_visible':False,'$scroll_box_visible_touch':False,
            '$scroll_box_mouse_image_control':ns+'.invisible','$scroll_box_touch_image_control':ns+'.invisible'},
    }
    slider={'$slider_box_size':[4,10]}
    for state in ('default','hover'):
        for kind in ('background','progress'):
            slider['$%s_%s_control'%(kind,state)]=ns+'.invisible'
    for state in ('','_hover','_locked','_indent'):
        slider['$slider_box%s_layout'%state]='common.empty_panel'
    for state in ('default','hover'):
        names=['slider_background','slider_progress'] if state=='default' else ['slider_background_hover','slider_progress_hover']
        skin['slider_bar_'+state]={'type':'image','texture':tex+'transparent','controls':[{'sizing_panel':{
            'type':'panel','controls':[{n+'@ModernProjection.invisible':{}} for n in names]}}]}
    slider['controls']=[{'slider_box@common.slider_box':{'$slider_box_layout':'$slider_box_layout',
        '$slider_box_size':'$slider_box_size','$slider_track_button':'$slider_name'}},
        {'slider_bar_default@ModernProjection.slider_bar_default':{}},
        {'slider_bar_hover@ModernProjection.slider_bar_hover':{'visible':False}}]
    skin['slider@PyreactBase.slider']=slider
    path=ROOT/'resource_pack/ui/ModernProjection.json'
    path.write_text(json.dumps(skin,ensure_ascii=False,indent=2),encoding='utf8')
    base_path=ROOT/'resource_pack/ui/PyreactBase.json'
    base=json.loads(base_path.read_text(encoding='utf8'))
    controls=base['rootBase']['controls']
    for suffix,target in [('label','label'),('type','type_image'),('input','input'),('slider','slider'),('doll','doll'),('scroll','scroll'),('round','round'),('click_observer','click_observer'),('pointer','pointer'),('inventory_modal','inventory_modal'),('motion_group','motion_group')]:
        key='mp_%s_tmpl@ModernProjection.%s'%(suffix,target)
        if not any(key in c for c in controls):
            controls.append({key:{}})
    base_path.write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf8')
    defs=ROOT/'resource_pack/ui/_ui_defs.json'
    data=json.loads(defs.read_text(encoding='utf8'))
    if 'ui/ModernProjection.json' not in data['ui_defs']:
        data['ui_defs'].append('ui/ModernProjection.json')
    defs.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--font',required=True); args=parser.parse_args()
    sprites(args.font); graphics(); native_skin()
    # Runtime names and future UI captions must not depend on scanned literals.
    from generate_font_atlas import build
    build(Path(args.font))
