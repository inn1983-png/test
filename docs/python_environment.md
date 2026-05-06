# Python 环境与依赖管理规范

## 核心结论

当前阶段，00–10 所有子系统共用同一个 Python 环境。

原因：

```text
1. 方便总控系统统一调用
2. 方便 00_common 公共工具复用
3. 方便 Codex 理解项目结构
4. 方便本地调试和联调
5. 避免每个子系统一个环境导致路径、依赖、显存释放混乱
```

---

# 一、共用根目录依赖

统一依赖文件：

```text
requirements.txt
```

安装：

```bash
pip install -r requirements.txt
```

所有模块都可以使用：

```text
00_common/
```

包括：

```text
io_utils.py
workspace_manager.py
module_runner.py
base_module.py
artifact_db.py
artifact_registry.py
artifact_resolver.py
resource_manager.py
```

---

# 二、为什么暂时不拆多个 Python 环境

不建议现在就做：

```text
01_novel_parser/venv
02_script_writer/venv
07_storyboard_image/venv
08_audio/venv
09_video/venv
```

原因：

```text
1. 总控调用复杂
2. 模块之间路径传递复杂
3. Codex 修改成本高
4. 本地测试麻烦
5. 资源释放和异常处理更难统一
```

---

# 三、重型模型依赖怎么处理

重型依赖不要一开始全部装。

例如：

```text
torch
transformers
accelerate
moviepy
pydub
ComfyUI 相关依赖
CosyVoice2 相关依赖
LTX / Wan / 视频模型依赖
```

这些依赖只在对应模块真正开发时再启用。

推荐策略：

```text
基础依赖写入 requirements.txt
重型依赖先注释
后续按模块逐步开启
```

---

# 四、模块共用 Python，但模型进程可以独立

虽然所有子系统共用 Python 环境，但本地模型服务可以独立运行。

例如：

```text
本地 LLM 服务
ComfyUI 服务
CosyVoice2 服务
LTX 视频服务
Qwen-VL 视觉理解服务
```

模块通过 API 或本地脚本调用这些服务。

模块完成任务后，必须执行：

```python
resource_manager.release_local_resources(MODULE_NAME)
```

---

# 五、什么时候考虑拆环境

只有当出现以下情况时，才考虑给某些模块单独环境：

```text
1. 生图模块和音频模块依赖强冲突
2. 视频模型依赖版本和 LLM 依赖严重冲突
3. 某个模型必须固定特殊 CUDA / torch 版本
4. 单一环境无法稳定运行
```

即使拆环境，也要保持：

```text
00 总控系统统一调度
运行数据仍写入 workspace
产物仍登记 artifacts.db
关键输出仍写入 manifest.json
```

---

# 六、当前最高规则

```text
当前阶段：所有子系统共用一个 Python 环境。
未来阶段：只有依赖冲突严重时，才允许按重型模块拆独立环境。
```
