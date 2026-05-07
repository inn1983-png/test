# Web UI 单模块运行与本地 Gemma 默认配置补充记录

日期：2026-05-07

## 本次改动

1. 在 Web UI 生产控制台新增“单模块运行”区。
2. 新增独立按钮：
   - 只运行 01 小说解析
   - 只运行 02 剧本改编
   - 只运行 03 角色库
   - 只运行 04 场景库
   - 只运行 05 道具库
   - 只运行 06 单帧分镜
   - 只运行 07 分镜图
   - 只运行 08 音频
   - 只运行 09 视频
   - 只运行 10 最终合成
3. 每个单模块按钮都直接调用 `--only-module`，避免用户误点 0-10 / 0-6 这类范围按钮。
4. `00_main_controller/run_pipeline.py` 新增 `--to-module` 参数，用于后续范围运行精确停止在指定模块。
5. Web UI 页面默认填入用户本地 LLM 配置：
   - `AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8080/v1/chat/completions`
   - `AI_DRAMA_LLM_MODEL=gemma-4-31B-it-Q4_K_M.gguf`
   - `AI_DRAMA_LLM_TEMPERATURE=0.1`
   - `AI_DRAMA_LLM_TIMEOUT_SEC=6000`
6. `start_web_ui.bat` 同步设置上述默认环境变量。
7. 新增 `web_ui/static/quick_controls.css`，用于单模块按钮区样式。

## 目标

UI 不再要求用户通过下拉框猜模块，也不再把“只跑 01”混在范围运行按钮里。
用户进入生产控制台后，可以直接点击“只运行 01 小说解析”。

## 后续建议

1. 继续让 Web UI server.py 传递 `to_module`，使“01-06 文本资产链路”按钮可以真正停在 06。
2. 在实时日志顶部显示最终命令，例如：
   `python 00_main_controller/run_pipeline.py --mode project --project-id xxx --only-module 01_novel_parser`
3. 增加依赖存在性检测提示：01 无依赖，02 依赖 01，03/04/05 依赖 01+02，06 依赖 02+03+04+05。
