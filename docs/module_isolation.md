# 模块隔离与本地显存释放规范

本项目采用“一个文件夹 = 一个独立系统”的架构。

核心目标：

1. 打磨任意一个子系统，不影响其他子系统。
2. 每个子系统只通过文件输入输出交接，不依赖其他模块的运行中状态。
3. 所有本地 LLM、生图、生视频、视觉理解模型，在本模块任务完成后必须释放显存。
4. 后续可以自由组合模块文件夹，形成不同流水线。

---

## 一、模块之间禁止强耦合

错误做法：

```python
from 02_script_writer.xxx import internal_function
```

正确做法：

```text
02_script_writer/output/script.json
        ↓
06_storyboard/input/script.json
```

模块之间只允许通过这些内容交接：

- JSON 文件
- TXT / MD 文件
- 图片文件
- 音频文件
- 视频文件
- 配置文件

不允许依赖另一个模块里正在运行的模型实例、Python 对象、临时变量。

---

## 二、每个模块固定结构

```text
module_name/
├─ input/                 # 本模块输入
├─ output/                # 本模块输出
├─ prompt.md              # 本模块提示词
├─ rules.md               # 本模块规则
├─ module_config.json     # 本模块配置
├─ run.py                 # 本模块入口
└─ README.md              # 本模块说明
```

---

## 三、本地模型使用原则

本项目所有模型都默认本地部署，包括：

- LLM
- 生图模型
- 生视频模型
- 视觉理解模型
- TTS / 音频模型

每个模块可以启动或调用自己的本地模型服务，但必须遵守：

```text
加载模型 → 完成本模块任务 → 写入 output → 释放显存 → 结束进程
```

不要让模型实例跨模块共享。

---

## 四、显存释放规则

每个涉及本地模型的模块，必须使用：

```python
try:
    # module task
    pass
finally:
    resource_manager.release_local_resources(MODULE_NAME)
```

公共释放逻辑在：

```text
00_common/resource_manager.py
```

目前包含：

- Python gc 回收
- PyTorch CUDA cache 释放
- 可扩展的本地清理命令

后续如果接入 ComfyUI、Ollama、vLLM、llama.cpp、CosyVoice2、LTX、Qwen-VL 等，都在这里扩展对应卸载逻辑。

---

## 五、模块组合规则

总控文件：

```text
pipeline.json
```

示例：完整流水线

```json
{
  "pipeline": [
    "01_novel_parser",
    "02_script_writer",
    "03_character_library",
    "04_scene_library",
    "05_prop_library",
    "06_storyboard",
    "07_storyboard_image",
    "08_audio",
    "09_video",
    "10_final_assembly"
  ]
}
```

示例：只打磨剧本系统

```json
{
  "pipeline": [
    "02_script_writer"
  ]
}
```

示例：只打磨分镜图系统

```json
{
  "pipeline": [
    "07_storyboard_image"
  ]
}
```

---

## 六、最高原则

不要做一个巨大的一体化工作流。

要做：

```text
独立模块库 + 总控组合器
```

这样才能做到：

```text
哪个模块不好，只改哪个模块。
哪个模型不好，只换哪个模块。
哪个流程不需要，就从 pipeline.json 里删掉。
```
