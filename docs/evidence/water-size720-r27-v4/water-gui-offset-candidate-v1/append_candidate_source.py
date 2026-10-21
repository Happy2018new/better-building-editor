"""Record prepared private source and successive unlaunched lifecycle controls."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
ROUND = WORK.parent
DOC = ROOT / 'docs/verification/WATER_CAPTURE_R27.md'


def sha(relative):
    return hashlib.sha256((ROUND / relative).read_bytes()).hexdigest()


def main():
    heading = '## 04:12—04:29：独立GUI候选源与正常Scene三GUI入口冻结'
    assert heading not in DOC.read_text('utf-8')
    text = '''

%s

root已独审三文件接口方向，仅批准私有候选。新的枚举源位于 `.runtime/projects/water-r27-gui-offset-v1`，source仍4484项、aux1391项，只改已声明的widgets、Product deployment与Scene三个文件；source合同 `45985a50b720b72cd9dd55a68cdeb7064fffa7201c79084b1ec8953ca11d5424`，manifest SHA `f187a7f6f5dd17b2d870af27c86f72c433cffeb1f2d98cbd4fc80e07a36103ae`。新archive119616132B，逐5875项bytes验证；旧源、诊断资源、原owner/qualification与共享生产文件均未回写。这个枚举源仍不是完整传递闭包，不授最终合流资格。

初始未启动host v1离线复核发现，native readback的单次RPC需要显式import Theme，不能依赖上一RPC全局；另加固定scene child900秒预算。v2随后执行实际launcher前置，在Popen前被原PROJECT身份断言拒绝：泛文本owner替换误碰了同名源目录basename。原v1/v2文件与失败输出保留，均没有创建watcher/session/MC。v3在owner替换后从精确source binding独立固定PROJECT，原70个launcher AST节点、actual bootstrap源/dispatch、core精确LF bytes、完整source/archive与生命周期imports通过。v3也未启动。

最终v4将每GUI控制顺序改为dry→wet，使窗口调整时可见水保留；GUI3和GUI2真实resize后，在任何下一次LOAD前保存同document ID、原source cells、原group keys的事件刷新与像素。ready_request是否相同如实记录，因为GUI改变控件size也可能改变pose，不能把不同请求冒称同一请求。原v3准备不覆盖。最终owner `water-r27-gui-scene-v4`，plan SHA `e6a3ef408d971e79a7fb37948ad4b7470a568d83e969d28648b07b54f89487c2`，host binding SHA `03fa2951e2e2a0736daf02a9b3605ff8c346ad73b303070f3f64048e134991fb`；v4静态70节点报告 SHA `%s`。此时仍无新MC。

三GUI固定计划为GUI4 `[1994,1105]`、GUI3 `[1600,900]`、GUI2 `[1280,720]`，actual GUI由SDK取整读回。每GUI的source tilted、flow_east tilted、含水fence front/tilted各保留dry/wet，24图；另有两张原文档可见水resize接缝，共26静态图。正常路径为原 `source_document → Session._loaded → owner.open_workspace → Scene`，不用诊断Panel wrapper；显式bootstrap仍不授默认生产入口。另一个独立subcontrol在Workspace关闭时真实resize，显式 `Theme.configure(3,True)` 验samefont缓存；它与正常Workspace挂载时的事件刷新观察分列。

12项新host控制在实际Python2执行原EXTRA_STATE payload，显式fake SDK/模型/UI，验证它自行解析Theme import和hidden size0；固定geometry政策拒绝错GUI、位置、尺寸、ID、surface隐藏、未ready和非有限值。实际restore helper控制证明先关Workspace，再原blueprint恢复factory/editor，最后恢复grid/Theme及profile/factory身份；合成restore IO失败仍传播而不声称恢复。report SHA `8055535eb53b6db19e9d93c7c4ace9a086a7016142116efe0a576dd97f7dec7e`。

另在真实Python2直接执行**未改的LiquidControls类**，对已经ready且相同request验证geometry先SetPosition/SetSize、后ready_request早退；不重新提交模型，稳定geometry第二次也不重复setter。两个控制通过，report SHA `%s`，native setters和renderer是显式fake，不能替代真实Scene。三文件scope review实际扫描files>0；Product deployment无finding，Scene与widgets只保留原有大函数/多参数风格告警；没有新增事件监听、跨端或逐group SDK调用。

最终组复用已审ordinary stop与精确身份/helper回收链，固定Scene child900秒；场景恢复先close等待导航结束，再原blueprint RESTORE，再自有grid/Theme/profile/factory检查与独立只读actors/source。总预计12—15分钟、保留20分钟窗口。root尚未授启动窗口时不启动；正式A、最终owner/default gate与用户人工关闭数仍无变化。
''' % (heading,
       sha('water-gui-offset-static-v4/static-launch-review-v1.json'),
       sha('water-gui-offset-candidate-v1/geometry-cache-py2-v1.json'))
    with DOC.open('ab') as output:
        output.write(text.encode('utf-8'))
    print('Appended private source and unlaunched v4 Scene plan')


if __name__ == '__main__':
    main()
