# 01 小说解析系统

## 模块定位

小说解析系统是整个流水线的第一步。

它不负责写剧本，不负责分镜，不负责生成角色图。

它只负责把原始小说文本拆干净，提取后续模块需要的基础信息。

## 输入

```text
01_novel_parser/input/novel.txt
```

## 输出

```text
01_novel_parser/output/novel_analysis.json
```

## 主要任务

1. 识别章节信息
2. 提取剧情主线
3. 提取关键冲突
4. 提取人物初始清单
5. 提取场景初始清单
6. 提取道具初始清单
7. 提取时间线
8. 提取情绪节奏
9. 标记适合改编成短剧的高刺激片段

## 最高原则

本模块只做“解析”，不做“改编”。

禁止在本模块里：

- 改写小说
- 扩写剧情
- 压缩成剧本
- 生成分镜
- 生成图像提示词

## 与后续模块的关系

```text
01_novel_parser/output/novel_analysis.json
        ↓
02_script_writer/input/novel_analysis.json
        ↓
03_character_library/input/novel_analysis.json
        ↓
04_scene_library/input/novel_analysis.json
        ↓
05_prop_library/input/novel_analysis.json
```

## 显存释放

本模块未来会调用本地 LLM。

运行结束后必须执行：

```python
resource_manager.release_local_resources(MODULE_NAME)
```

当前 `run.py` 已经内置该释放逻辑。
