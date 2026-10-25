# R29：私有 runtime ZIP 与独立来源绑定

本包保存 `.runtime/library-runtime-package-r29-v1` 的全部顶层记录／脚本（排除runtime ZIP）、独立 `library-runtime-source-binding-r29-v1` 五份交付物及打包／扫描程序。原 runtime ZIP 为 **47,280,551 B**，SHA-256 **`f42cdd600b2783fb5dfc1940ed28991de547880123dcd48b45fa3e27c7ee5eed`**，保留在原私有路径，没有复制进Git或本证据包。

ZIP实际为 **3738 runtime + 2 license + 1 receipt = 3741成员**，payload119,444,106 B。3738 runtime来自3716个CPU-v8 host文件和29个sealed dcf overlay，其中覆盖7、新增22。状态库声明仍为 **NEMC 3.9.0.401155**；本包不授予3.10或原生引擎资格。

## 原v1 builder与外部来源审计

v1 builder实测核物理输入raw SHA、ZIP清单／长度／SHA、vendor lock、两库manifest／license／runtime模块、renderer→states绑定和3项renderer资源；原生pack manifest与modMain只验证存在和精确字节，**没有执行SDK入口**。生成的成员均为regular file。

外部 `bind.py` 是后来另行执行的只读增强，不倒写成v1 builder自带门禁。它验证CPU-v8成功／before=after、full成功／before=after，把3738 runtime逐项关联到真实ZIP、物理来源、完整回归的前后清单及实际private p。CPU-v8全部6333输入259,545,173 B、full全部6989输入326,464,656 B各实际回读两次，404个完成时产品import重新绑定；3740 payload均核raw SHA／长度，3741成员另核regular属性、路径和casefold不碰撞。结果和全部源／构建记录未变，审计耗时87.262449秒。完整回归仍记3613／skip10，不因本归档改写或重跑。

## 保留的准备失败与最终真实ZIP导入

初次构建在license预检因clean worktree CRLF与Git LF的SHA差异失败，尚未写包或receipt。`preparation-history.json`明确只是观察到工具输出的**摘要，不是raw stderr**。后续保留物理license字节，只允许CRLF→LF等价并在receipt中记录双SHA。

原 `controls-result.json` 保存**一次**正检查与**5个实际完整物理ZIP负控**：缺adapter、改vendor字节、重复成员、`../outside.txt`、改lock，全部拒绝。重复成员的原warning保留。原driver每次只创建一个exactpath派生包并unlink；本次核5个exactpath均已不存在，没有新增删除或重跑，也没有复制这5个约47MB派生包。

初Py2 ZIP导入已执行纯模块及调用，但driver把13个sys.modules None隐式相对导入缓存哨兵误当outside，assert失败；原stderr保留。v2显式排除并披露这些缓存后，在输出OS路径的JSON编码阶段又发生实际filesystem codec错误，零字节result／stdout和stderr原样保留。v3只修OS路径报告字段的解码，原两次失败记录、初/v2/v3 driver与Py3中间成功结果全部保留，不覆盖历史。

最终v3的真实 **CPython 2.7.13／3.13.13 各导入60个产品模块**，全部从实际ZIP读取，逐模块raw SHA对receipt；无outside、无SDK import或SDK stub。确认state adapter函数／operations与vendored库对象身份、9项layout导出身份，并执行有限stairs变换／context往返／投影size调用；不是重跑完整产品矩阵。Py2的13个None缓存单列，Py3为0。五个物理ZIP负控没有随导入driver修正重复运行。

这些是隔离宿主的纯模块ZIP导入，**不是普通游戏冷启动、编辑器／完整投影／缺失投影三路径，亦非发布、GPU或人工验收**。没有MC／RPC／世界写入或新增资格，人工关闭0。

## 精简归档及复建边界

39份逻辑引用，31个唯一gzip对象；逻辑原文9,464,755 B、去重原文9,428,115 B、gzip共1,381,839 B，最大对象718,410 B。对象名是raw SHA，index另列storage SHA／长度；filename为空、mtime=0、level=9，重复压缩字节相同。新进程verification解压回读全部引用、再核原输入和runtime ZIP SHA未变，并复扫选定原文、JSON解码字符串和元数据。

`physical-inputs.json`、receipt、builder及外部绑定记录精确原路径、长度、SHA和CPU／overlay／full关联。复建仍需原封存CPU-v8 manifest、dcf overlay provenance及所列精确物理源文件；本包没有119MB runtime源，也不能仅凭一个Git提交独立复建。压缩实现／环境差异下不承诺新建ZIP逐字节同SHA。运行历史driver必须改用fresh输出，不覆盖原件；本归档没有执行这些driver。
