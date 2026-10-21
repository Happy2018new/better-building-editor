"""Append completed immutable observer results to the water-owned verification note."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
ROUND = WORK.parent
DOC = ROOT / 'docs/verification/WATER_CAPTURE_R27.md'


def sha(relative):
    return hashlib.sha256((ROUND / relative).read_bytes()).hexdigest()


def main():
    heading = '## 03:50—03:59：v2真实UI几何、38张独立原生对照及精确释放'
    assert heading not in DOC.read_text('utf-8')
    text = '''

%s

root独审实际70个launcher AST节点、共用reader及固定单次followup hold策略后，v2以新owner `water-r27-ui-geometry-v2` 启动唯一session。原bootstrap core精确LF字节不变，源仍为独立diagnostic的4484项与1391辅助。plan SHA `1045326cad31196f4bed32d453dd3e0f0e55456291871036387e5c6c0ba2e0c9`，host binding SHA `4aff1e8f737720ccc630ed6675e502c624e0baff25e4cce4753d7e8cee0bf698`。固定hold只允许root原子授权的精确SHA脚本 `root-followup.py` 执行一次，最长600秒；没有通用job queue或任意路径执行。

实际game `68020 / 134370858444454299`，MCDK `36612 / 134370858442452820`。冷启103.6927秒、bootstrap11.8236秒，初始12状态49.2356秒。GUI4/3/2分别一次挂载执行 `empty_before → stone → neutral15 → empty_after`；逻辑ready后各保留6样本、0.2秒间隔，阶段间独立恢复再resize/remount。可见Panel wrapper持续存在且SDK尺寸/全局位置符合声明；该结构变化仍只属于诊断UI，不授原生产控件资格。所有hidden Doll实测size0；可见stone确有正常像素但 `GetModelId=-1`，原helper三组矛盾原样保留，不能把skeleton的model-ID语义移植为block_geometry门。neutral可见bank的native与renderer ID一致。

SDK logical/ScreenView实测GUI4为 `[499,277]/[1995,1107,0,0]`、GUI3为 `[533,300]/[1600,900,0,0]`、GUI2为 `[641,360]/[1281,720,0,0]`。ScreenView是公开SDK取整后的视角，不冒称原始物理客户区。几何观测原report SHA `%s`。

同session内root授权固定followup（SHA `bde1df192369df5152a8f4f0808f1478bb622f456190f9ea518782f608c792af`），实际完成38/38张：GUI4 wide/front；GUI2 wide/front、tilted及原六轴单变量控制；empty、独立stone、anchor15 zero/quarter/inverseGUI、anchor0 zero及五类native矩阵。GUI3仅有上述SDK几何，尚无像素。原138项plan和宿主断言不改，新host只在独立诊断子集中单列已知stone -1语义；不得回授原门通过。capture report SHA `%s`，原PNG全部留存。

固定全图分析器未修改，原RGB64±5、相对empty贡献>20、双向2px度量及97负控照旧。GUI2 front quarter IoU0，inverseGUI IoU0.972449；tilted quarter0.004002、inverseGUI0.973958；对应三轴inverseGUI约0.954707—0.974222。原全图neutral mask明确混入屏幕顶部debug灰文字，bounds因此过大；原分数和负控仍保留，不借新scope覆盖或改阈值。原分析report SHA `%s`。

root另外在采集前已声明、且SDK实际确认的 `viewport_parent` 全矩形内做派生测量，矩形按SDK几何换算，未按图片搜索ROI、未平移/缩放拟合；沿用同一RGB64±5、贡献>20及2px。该新scope中GUI4 quarter IoU0.98387、GUI2 front inverseGUI0.97531、tilted inverseGUI0.97963，三轴约0.97963，双向2px recall全部1；主体y约差1px。GUI2 quarter front仍相差约111px/IoU0，tilted仍约111px/IoU0.004。它支持GUI偏移候选，不能代替原全图结果、GUI3像素、产品Scene或正式A。派生report SHA `%s`。

独立矩阵因子分析继续按原signed24各项±1/4096的误差界检查 `WVP≈PROJ·WV`：GUI4 front最大ratio0.406805、GUI2 tilted0.792074；**GUI2 front为1.190508，原样失败**，不放宽量化界、不声称已证实机制。native geometry跨五矩阵一致。`+1.5 entityY` 在front屏幕位移为0、tilted约 `(+68.90625,-41.66016)px`，因此保留旋转pivot，不能当成GUI偏移删掉。因子report SHA `%s`。

group共524.8296秒，root核图与独立after-followup恢复后原子release。最终restored/source_unchanged为true、cleanup_errors空、bootstrap marker显式retired；continuous guard484样本，无句柄/modal breach。普通owner stop返回0；same-handle observer随后实测game于03:59:17.861退出 `0xC0000409`，MCDK于03:59:17.865退出0，精确创建身份均消失；不把game退出码写成引擎正常退出。watcher `66748 / 134370858335265484` 已精确回收，水MC窗口完整释放给变换专项。

## 自定义水GUI偏移窄候选准备

仅在 `.runtime/round-20261022/water-gui-offset-candidate-v1/candidate/` 准备三份私有文件：`widgets.py`把原configure已经计算的整数gui存为 `Theme.native_gui_scale`，赋值在字体/主题early-return之前；`liquid_product_deployment.py`只给显式Product水profile添加 `ui_offset_for_gui(size,gui)=(0,min(size)/gui)`，unknown/非正整数/非有限值拒绝；`scene.py`仅水分支使用可选接口，legacy profile仍用原callback。其他item/cauldron/portal/book分支AST不变；不新增tick/group内SDK读取，不改shader、pivot、生成owner或qualification数据。共享生产源和原冻结snapshot未改。

真实Python2执行29控通过，覆盖GUI4/3/2同字体5.0时仍刷新cache、取整SDK比例、invalid GUI、Product dynamic/frozen实例绑定、300组真实Scene水闭包访问无额外FFI、legacy fallback、四个其他profile AST同值，以及原resize闭包 `.05/.25` 调度下物理尺寸单独变化和最终逻辑变化均调用configure。SDK/构造器/UI render是显式fake边界，不冒称真实窗口resize或水原生像素验收。第一次fixture因文件系统路径混用unicode失败，第二次因Python2的list.append不可hash失败；仅纠正fixture，三份候选bytes未改，原fixture留存。最终controls report SHA `%s`。

候选随后仍需root独审、独立新source合同及三GUI正常workspace/Scene实机；原生产构造因资格与owner不符继续拒绝，显式bootstrap不能授默认入口资格。正式A、最终owner、默认路径、GUI3像素和产品GUI修复均未关闭；本水专项新增用户人工关闭0。
''' % (heading,
       sha('water-ui-geometry-observer-v2/geometry-observation-v1.json'),
       sha('water-ui-geometry-observer-v2/anchor-followup-capture-v1.json'),
       sha('water-ui-geometry-observer-v2/neutral-matrix-analysis-v1.json'),
       sha('root-water-native-viewport-measurement-v1/report.json'),
       sha('water-ui-geometry-observer-v2/matrix-factor-analysis-v1.json'),
       sha('water-gui-offset-candidate-v1/controls-py2-v3.json'))
    with DOC.open('ab') as output:
        output.write(text.encode('utf-8'))
    print('Appended completed observer results and private candidate scope')


if __name__ == '__main__':
    main()
