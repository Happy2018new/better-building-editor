# -*- coding: utf-8 -*-
"""Tool descriptions are shared by the UI, search, help and regression tests."""
from __future__ import unicode_literals

GROUPS = [('select', '选区', 'cursor'), ('edit', '编辑', 'brush'),
          ('transform', '变换', 'move'), ('shape', '形状', 'cube'),
          ('pattern', '纹理', 'grid'), ('finish', '修整', 'spark')]

# id, group, title, hint. Every entry is dispatched by Editor.run.
TOOLS = [
    ('select_all', 'select', '全选区域', '选择整个建筑范围。'),
    ('select_nonair', 'select', '选择方块', '仅选择已有方块的位置。'),
    ('select_air', 'select', '选择空气', '仅选择空白位置。'),
    ('select_material', 'select', '同类材质', '选择与替换来源相同的方块。'),
    ('select_layer', 'select', '当前图层', '选择当前 Y 层。'),
    ('select_invert', 'select', '反向选择', '反转当前选择的格子。'),
    ('select_expand', 'select', '扩展选区', '沿六个方向扩展一个方块。'),
    ('select_contract', 'select', '收缩选区', '沿六个方向收缩一个方块。'),
    ('select_surface', 'select', '选择表面', '选取与空气接触的方块表面。'),
    ('select_box', 'select', '坐标框选', '使用参数中的起点与终点框选。'),
    ('fill', 'edit', '填充方块', '用主材质填满选区。'),
    ('erase', 'edit', '清空选区', '删除选区内的方块，可以撤销。'),
    ('replace', 'edit', '替换材质', '将来源材质替换为主材质。'),
    ('fill_air', 'edit', '仅填空气', '保留已有建筑，只填空白。'),
    ('paint', 'edit', '表面涂装', '为暴露的方块更换材质。'),
    ('copy', 'edit', '复制选区', '复制相对坐标和材质到内部剪贴板。'),
    ('cut', 'edit', '剪切选区', '复制并移除选区内方块。'),
    ('paste', 'edit', '粘贴方块', '以参数起点为原点粘贴；越界时拒绝。'),
    ('paste_airless', 'edit', '无空气粘贴', '仅粘贴剪贴板中的非空气方块。'),
    ('flood', 'edit', '连通填充', '从参数起点开始，填充六向连通的同类方块。'),
    ('swap', 'edit', '交换材质', '交换主材质和来源材质。'),
    ('rotate_y90', 'transform', '水平旋转 90°', '围绕选区中心旋转，保留块状材质属性。'),
    ('rotate_y180', 'transform', '水平旋转 180°', '将选区水平转向相反方向。'),
    ('rotate_y270', 'transform', '水平旋转 270°', '围绕选区中心逆向旋转。'),
    ('mirror_x', 'transform', '沿 X 镜像', '左右翻转选区内的方块。'),
    ('mirror_y', 'transform', '沿 Y 镜像', '上下翻转选区内的方块。'),
    ('mirror_z', 'transform', '沿 Z 镜像', '前后翻转选区内的方块。'),
    ('move_xp', 'transform', '向东移动', '沿 X 正方向移动步长个方块。'),
    ('move_xn', 'transform', '向西移动', '沿 X 负方向移动步长个方块。'),
    ('move_yp', 'transform', '向上移动', '沿 Y 正方向移动步长个方块。'),
    ('move_yn', 'transform', '向下移动', '沿 Y 负方向移动步长个方块。'),
    ('move_zp', 'transform', '向南移动', '沿 Z 正方向移动步长个方块。'),
    ('move_zn', 'transform', '向北移动', '沿 Z 负方向移动步长个方块。'),
    ('stack_x', 'transform', '沿 X 阵列', '按选区宽度复制一次；预先检查边界。'),
    ('stack_z', 'transform', '沿 Z 阵列', '按选区深度复制一次；预先检查边界。'),
    ('box', 'shape', '实心长方体', '在选区内生成实心长方体。'),
    ('shell', 'shape', '空心长方体', '生成厚度可调的闭合外壳。'),
    ('walls', 'shape', '四面围墙', '仅生成四周墙体，保留顶和底。'),
    ('frame', 'shape', '方框骨架', '沿长方体十二条边生成骨架。'),
    ('sphere', 'shape', '实心椭球', '按选区宽高深生成椭球。'),
    ('sphere_shell', 'shape', '空心椭球', '生成厚度可调的椭球壳。'),
    ('cylinder', 'shape', '实心圆柱', '沿 Y 轴生成椭圆截面的圆柱。'),
    ('tube', 'shape', '空心圆柱', '生成环形圆柱，可用于塔楼。'),
    ('pyramid', 'shape', '金字塔', '从底到顶收拢的四棱锥。'),
    ('dome', 'shape', '半球穹顶', '生成适配选区的上半椭球壳。'),
    ('arch', 'shape', '圆拱门', '沿 Z 方向生成圆拱与两侧立柱。'),
    ('stairs', 'shape', '阶梯结构', '沿 X 方向生成逐级升高的实心楼梯。'),
    ('line', 'shape', '空间直线', '连接参数起点与终点。'),
    ('floor', 'shape', '铺设地板', '铺满选区最底层。'),
    ('roof', 'shape', '双坡屋顶', '沿 X 方向生成对称的双坡顶。'),
    ('checker', 'pattern', '棋盘拼色', '用主副材质生成三维棋盘纹理。'),
    ('stripe_x', 'pattern', '纵向条纹', '沿 X 方向按步长交替主副材质。'),
    ('stripe_y', 'pattern', '分层条纹', '沿 Y 方向交替主副材质。'),
    ('stripe_z', 'pattern', '横向条纹', '沿 Z 方向按步长交替主副材质。'),
    ('noise', 'pattern', '随机混合', '按混合比例与固定种子生成可复现纹理。'),
    ('gradient', 'pattern', '高度渐变', '从底到顶逐渐增加副材质比例。'),
    ('brick', 'pattern', '砖缝排列', '错缝砖纹，步长控制砖块宽度。'),
    ('lattice', 'pattern', '网格镂空', '生成主材质框架和副材质连接点。'),
    ('hollow', 'finish', '掏空内部', '删除未与空气接触的内部方块。'),
    ('clean_isolated', 'finish', '清理孤点', '移除六个方向均为空气的孤立方块。'),
    ('fill_holes', 'finish', '修补孔洞', '填充六个方向均为方块的单格孔洞。'),
    ('gravity', 'finish', '垂直压实', '按列将方块从选区底部向上紧密排列。'),
    ('foundation', 'finish', '向下打基', '将每列已有最低方块向下延伸到选区底。'),
    ('heightmap', 'finish', '保留顶面', '每列仅保留最高的方块。'),
]
BY_ID = dict((item[0], item) for item in TOOLS)

# Stable semantic icons shared by tool lists and compact controls.
TOOL_ICONS = {
    'select_all': 'select_all', 'select_nonair': 'cube', 'select_air': 'box_outline',
    'select_material': 'pick', 'select_layer': 'layers', 'select_invert': 'invert',
    'select_expand': 'expand', 'select_contract': 'contract', 'select_surface': 'surface', 'select_box': 'select_box',
    'fill': 'fill', 'erase': 'erase', 'replace': 'replace', 'fill_air': 'fill', 'paint': 'brush',
    'copy': 'copy', 'cut': 'cut', 'paste': 'paste', 'paste_airless': 'paste', 'flood': 'drop', 'swap': 'replace',
    'rotate_y90': 'rotate_right', 'rotate_y180': 'rotate_right', 'rotate_y270': 'rotate_left',
    'mirror_x': 'mirror_x', 'mirror_y': 'mirror_y', 'mirror_z': 'mirror_x',
    'move_xp': 'arrow_right', 'move_xn': 'arrow_left', 'move_yp': 'arrow_up', 'move_yn': 'arrow_down',
    'move_zp': 'arrow_down', 'move_zn': 'arrow_up', 'stack_x': 'array', 'stack_z': 'array',
    'box': 'cube', 'shell': 'box_outline', 'walls': 'walls', 'frame': 'select_box',
    'sphere': 'sphere', 'sphere_shell': 'sphere', 'cylinder': 'cylinder', 'tube': 'cylinder',
    'pyramid': 'pyramid', 'dome': 'dome', 'arch': 'arch', 'stairs': 'stairs', 'line': 'line', 'floor': 'floor', 'roof': 'roof',
    'checker': 'invert', 'stripe_x': 'stripes_x', 'stripe_y': 'stripes_y', 'stripe_z': 'stripes_z',
    'noise': 'noise', 'gradient': 'gradient', 'brick': 'brick', 'lattice': 'grid',
    'hollow': 'box_outline', 'clean_isolated': 'spark', 'fill_holes': 'repair',
    'gravity': 'gravity', 'foundation': 'foundation', 'heightmap': 'surface',
}
ACTION_ICONS = {
    '左转': 'rotate_left', '右转': 'rotate_right', '俯视': 'top_view', '正视': 'front_view',
    '展开视图': 'expand', '还原视图': 'contract', '材质与属性': 'sliders', '隔离图层': 'layers',
    '恢复全选区域': 'select_all', '使用自定义材质': 'check',
    '仅显示当前层': 'layers', '显示全部图层': 'layers', '显示全部层': 'layers', '逐层投影': 'layers',
    '载入': 'folder', '重命名': 'edit', '删除': 'trash', '仅显示缺失方块': 'box_outline',
    '关闭投影': 'close', '同步空气（会清除对应位置）': 'erase', '撤销世界写入': 'undo',
    '减少动态效果': 'motion', '取消': 'close', '确认继续': 'check',
}
SEGMENT_ICONS = {
    '工作台': 'home', '建筑库': 'library', '投影': 'projection', '入门指南': 'info',
    '三维': 'cube', '逐层': 'layers', '参数': 'sliders', '图层': 'layers', '历史': 'history',
    '浏览': 'orbit', '选取': 'cursor', '放置': 'cube', '换材质': 'brush', '绘制': 'brush',
    '擦除': 'erase', '吸管': 'pick', '框选': 'select_box', '起点': 'pin', '终点': 'pin',
    '主材质': 'cube', '副材质': 'copy', '替换来源': 'replace', '蒙版来源': 'replace', '匹配材质': 'replace', '材质': 'cube',
    '全部': 'select_all', '方块': 'cube', '空气': 'box_outline', '来源': 'pick',
}


def tool_parameters(identity):
    """Only expose parameters actually consumed by this operation."""
    group = BY_ID[identity][1]
    values = set()
    if group in ('shape', 'pattern') or identity in ('fill', 'replace', 'fill_air', 'paint', 'flood', 'swap', 'fill_holes'):
        values.add('material')
    if group == 'pattern':
        values.add('secondary')
    if identity in ('replace', 'swap', 'select_material'):
        values.add('source')
    if identity in ('select_box', 'line'):
        values.update(('start', 'end'))
    if identity in ('paste', 'paste_airless', 'flood'):
        values.add('start')
    if identity in ('shell', 'walls', 'frame', 'sphere_shell', 'tube', 'dome', 'arch'):
        values.add('thickness')
    if identity.startswith(('move_', 'stripe_')) or identity in ('checker', 'brick', 'lattice'):
        values.add('step')
    if identity == 'noise':
        values.add('ratio')
    if identity in ('noise', 'gradient'):
        values.add('seed')
    return values

MATERIALS = [
    ('minecraft:quartz_block', 0, '石英', 'F0EDE5'),
    ('minecraft:concrete', 0, '白色混凝土', 'DFE3DF'),
    ('minecraft:planks', 0, '橡木', 'BD9564'),
    ('minecraft:planks', 1, '云杉木', '795C3C'),
    ('minecraft:stonebrick', 0, '石砖', '89918D'),
    ('minecraft:stone', 0, '石头', '8B9196'),
    ('minecraft:glass', 0, '玻璃', 'A8D6DD'),
    ('minecraft:stained_glass', 9, '青色玻璃', '54B2C7'),
    ('minecraft:leaves', 0, '树叶', '709968'),
    ('minecraft:grass', 0, '草方块', '83AD69'),
    ('minecraft:concrete', 15, '黑色混凝土', '303841'),
    ('minecraft:sea_lantern', 0, '海晶灯', 'C4E6DC'),
    ('minecraft:brick_block', 0, '红砖', 'AE7062'),
    ('minecraft:sandstone', 0, '砂岩', 'D9C897'),
    ('minecraft:wool', 0, '白色羊毛', 'ECECE4'),
    ('minecraft:air', 0, '空气', 'E5EAF0'),
]
