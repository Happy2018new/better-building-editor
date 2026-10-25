# R29 当前错误反馈源 CPU v5

产品源 `cdd0601537e2466dc336ddd46ad5ae6e6863fcad` 的实际工作区全量为 **3583项／skip1／OK、进程exit0**。unittest本体507.210秒，完整驱动521.585936秒。6330项behavior/resource/tests/tools输入、259,517,114字节，运行前后重新枚举hash完全一致，`changed_selected_inputs=[]`。包含历史untracked测试／工具，不称clean HEAD-only资格。

13个本轮实际变更产品模块在真Py2.7.13／Py3.13.13编译通过，编译回执逐文件SHA与本次输入清单匹配。没有写pyc，没有做runtime SDK导入。实际unittest结束为日志274／276行；后续mock失败JSON和traceback是负控注入输出，不是本轮全量失败。

8份原件确定性gzip去重为7个对象；原始与压缩SHA在`index.json`。解压后按references路径核验，before和after共享同一对象。编译回执的references路径保留原packager相对`.runtime/round-20261026`的位置；将原件用于复放前应据此恢复路径。新源投影v4、水v3分别冻结，原生网络／世界画面／人工仍另验，不能用本包替代。
