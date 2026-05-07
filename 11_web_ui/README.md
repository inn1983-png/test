# 11 Web UI：00–06 本地测试控制台

## 用途

这是给代码小白测试 00–06 用的最简本地网页。

它不参与核心生成逻辑，只负责：

```text
粘贴/保存小说输入
一键运行 01–06
单独运行某个模块
查看模块状态
查看各模块输出 JSON / TXT
查看运行日志
```

---

## 启动方式：Windows

双击或在命令行运行：

```bat
11_web_ui\start_windows.bat
```

启动后会自动打开浏览器：

```text
http://127.0.0.1:7860
```

如果没有自动打开，就手动复制上面的地址到浏览器。

---

## 启动方式：命令行

在项目根目录运行：

```bash
python 11_web_ui/app.py
```

---

## 使用步骤

1. 启动 UI。
2. 在“项目 ID”里填写：

```text
project_test_001
```

3. 把小说章节粘贴到输入框。
4. 点击“保存小说输入”。
5. 点击“一键运行 01–06”。
6. 等待日志结束。
7. 在“查看输出”里选择：

```text
01_novel_parser / novel_analysis.json
02_script_writer / script.json
03_character_system / characters.json
04_scene_system / scenes.json
05_prop_system / props.json
06_storyboard / storyboard.json
```

---

## 运行前必须配置本地 LLM

例如 Windows CMD：

```bat
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
set AI_DRAMA_LLM_TEMPERATURE=0.1
set AI_DRAMA_LLM_TIMEOUT_SEC=240
```

如果你的本地 LLM 服务没有启动，点击运行后会失败。

---

## 输出位置

小说输入保存到：

```text
workspace/projects/{project_id}/input/novel.txt
```

模块输出在：

```text
workspace/projects/{project_id}/01_novel_parser/
workspace/projects/{project_id}/02_script_writer/
workspace/projects/{project_id}/03_character_system/
workspace/projects/{project_id}/04_scene_system/
workspace/projects/{project_id}/05_prop_system/
workspace/projects/{project_id}/06_storyboard/
```

---

## 注意

这个 UI 是测试控制台，不是最终产品前端。

它暂时只覆盖 00–06：

```text
01 小说解析
02 剧本改编
03 角色库
04 场景库
05 道具库
06 单帧分镜
```

07 图片生成、08 音频、09 视频、10 合成后续再做。