# R29：真实写入与界面拒绝提示的中文错误

本轮沿实际 `WorldJob → server.reply → JSON → bridge.receive → TaskStatus` 检查时，发现两处可复现的 Python 2 编码缺陷。

SDK 以 UTF-8 字节给出错误时，`WorldJob.step` 原来的 Unicode 格式化会再次抛出 `UnicodeDecodeError`，失败格还没有计数，服务端任务仍占用且没有最终回复，客户端保持等待。Python 3 虽能结束，却会把原因显示成 `b'\\x...'`。另一处发生在投影方向改变后点击“应用到世界”：旧目标本来被正确拒绝，但 `Session.action` 对中文异常调用 `str`，Python 2 再抛 `UnicodeEncodeError`，界面没有显示拒绝原因。旧目标安全检查没有失效。

新增纯 `error_text.py` 统一转换这些原因：单个字节参数按 UTF-8 解码，非法字节保留替换符；普通异常转换为当前解释器的文本类型；仅在 SDK 自定义字符串触发 Unicode 错误时按实际字节回退。helper 没有运行时依赖。WorldJob 和 Session 的五处既有错误显示边界使用它，保留原捕获类型、清理、emit、默认提示及返回行为。没有扩大服务端请求或捕获合并等其他错误边界。

水、末地和书的 owner 来源声明显式加入新 helper，数量分别为42、20、20；书 BODY 来源不变。生成的 owner／qualification metadata 保持旧字节；这些声明与新源没有继承旧资格，后续独立实例须重新冻结。

私有候选保留真实 Py2.7.13／Py3.13.13 的原始失败和修后结果：18条实际反馈链、20个文本／Session控制通过。root 随后对集成后的实际源码另运行两个解释器，失败／取消／成功及公开旧目标拒绝链均正常；具体原因和首个坐标到达客户端，pending／busy清除，后续合法格继续，中途取消停止后续写入，延迟进度不覆盖最终消息。

新增5项永久回归覆盖实际上传、服务端写入、回复、JSON序列化和客户端接收，及错误文本和公开拒绝操作；连同WorldJob、Session、来源审计、书owner／末地集成，共67项定点通过。结构审查实际解析5个前缀匹配模块，只有既有Session长函数、world_capture参数和world_projection兼容异常提示。两次零文件scope结果不作为通过依据。

内部原件位于 `.runtime/r29-world-feedback-candidate/`，root独立回执为 `.runtime/r29-world-feedback-root-v3/`。这些是CPU及JSON边界验证，没有运行ModSDK网络、原生输入或文字像素检查，新增人工关闭数为0。bca源3571项完整回归仍仅对应该较早来源，不把其数字直接授给本修复。
