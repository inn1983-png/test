# 07_storyboard_image 工作流优化计划

## 目标

07 的目标不是一次把所有图片都生成得完美，而是先搭出可测试、可替换、可局部重跑的图片生产框架。

核心链路：

```text
07P 计划依赖图
→ 07A 角色定妆图
→ 07B 角色造型/换装图
→ 07C 场景/道具参考图
→ 07D 正式单帧分镜图
→ 07E 总检/registry/retry_plan
```

---

## 一、每一步推荐使用的 ComfyUI 工作流

### 07A_character_lock：角色定妆图

任务性质：文生图。

目标：先锁脸，不追求剧情动作。

推荐工作流：

```text
文生图基础模型
+ 人像质量增强
+ 面部细节修复
+ 可选人物一致性锁定节点
```

建议结构：

```text
Prompt 文本输入
→ 基础文生图模型
→ 人脸/五官增强
→ 高清修复
→ SaveImage
```

推荐模型方向：

```text
Flux / SDXL / 写实人像模型 / 古风写实模型
```

输出要求：

```text
单人
正面或 3/4 角度
背景干净
性别、年龄、气质稳定
不要复杂动作
不要多人
```

优先级：最高。

原因：后面所有换装图和分镜图都依赖定妆图。

---

### 07B_character_appearance：角色造型图 / 换装图

任务性质：图生图。

目标：同一张脸 + 指定服装 + 指定穿戴物。

推荐工作流：

```text
定妆图参考
+ 图生图
+ 人脸一致性节点
+ 服装/道具控制
+ 高清修复
```

建议结构：

```text
定妆图输入
→ 人脸一致性参考
→ Prompt 指定 costume_id / wearable_props
→ 图生图采样
→ 高清修复
→ SaveImage
```

可选节点方向：

```text
IPAdapter FaceID / PuLID / InstantID / Reactor / Face Detailer
```

输出要求：

```text
同一张脸
单人
服装清楚
道具穿戴位置明确
背景可简单
不做剧情动作
```

优先级：最高。

原因：正式分镜图不要再承担换装和锁脸压力。

---

### 07C_scene_reference：场景参考图

任务性质：文生图或登记已有图。

目标：生成稳定空间，不追求人物。

推荐工作流：

```text
文生图场景模型
+ 古代建筑/室内/街道场景提示词
+ 高清修复
```

建议结构：

```text
场景 Prompt
→ 文生图
→ 高清修复
→ SaveImage
```

输出要求：

```text
尽量空镜
空间结构清晰
光源稳定
无现代物品
不要人物抢画面
```

优先级：中高。

原因：场景稳定后，多人和道具融合会更稳定。

---

### 07C_prop_reference：道具参考图

任务性质：文生图或登记已有图。

目标：生成干净道具参考图。

推荐工作流：

```text
文生图静物模型
+ 背景干净
+ 材质细节
```

建议结构：

```text
道具 Prompt
→ 文生图
→ 高清修复
→ SaveImage
```

输出要求：

```text
单一道具
背景干净
材质真实
古代中国语境
不要现代工业感
```

优先级：中。

说明：不是所有道具都必须生成参考图，只处理本章真正重要或画面可见的关键道具。

---

### 07D_storyboard_frame：正式单帧分镜图

任务性质：多参考图融合 / 图生图。

目标：融合场景 + 角色造型 + 道具 + 剧情动作。

推荐工作流：

```text
场景图输入
+ 1-N 个角色造型图输入
+ 0-N 个道具图输入
+ Prompt 指定动作/构图/情绪
+ 多参考图融合
+ 局部人脸修复
+ 高清修复
```

建议结构：

```text
场景参考图
+ 角色造型参考图
+ 道具参考图
→ 多参考融合
→ Prompt 控制动作/构图
→ 采样
→ Face Detailer / 局部修复
→ SaveImage
```

可选方向：

```text
IPAdapter 多参考
Regional Prompt
ControlNet / Depth / Lineart
Inpaint 局部修脸
LayerDiffuse / 区域控制
```

输出要求：

```text
严格按 06 frame
人物数量正确
角色造型正确
场景一致
道具位置合理
锚点帧优先
普通帧可参考上一帧
```

优先级：最高。

---

## 二、最稳的测试顺序

不要一开始就全流程真实出图。

推荐顺序：

```text
1. dry_run 跑通 07P-07E
2. 只 execute 07A 定妆图
3. 只 execute 07B 换装图
4. execute 07C 场景/道具图
5. 只挑 3-5 帧 execute 07D 分镜图
6. 再全量 execute 07D
```

这样定位问题最快。

---

## 三、当前还需要优化的框架点

### 1. 单阶段选择性运行

需要支持：

```bash
python 07_storyboard_image/run_staged.py --only-stage 07A
python 07_storyboard_image/run_staged.py --only-stage 07D --frame-id frame_001
```

目的：本地测试时不用每次重跑全 07。

---

### 2. 任务级过滤

需要支持：

```text
只跑某个 canonical_name 的定妆图
只跑某个 appearance_asset_key
只跑某个 scene_key
只跑某几个 frame_id
```

---

### 3. workflow 输入槽位适配器

不同 ComfyUI 工作流节点输入方式不同，不能只支持 text / filename_prefix。

需要扩展 workflow_mapping：

```json
{
  "reference_image_slots": [
    {"node_id": "31", "input": "image", "source": "scene"},
    {"node_id": "32", "input": "image", "source": "character_appearance", "index": 0},
    {"node_id": "33", "input": "image", "source": "character_appearance", "index": 1}
  ]
}
```

---

### 4. 图片结果回收

ComfyUI 返回 history 后，需要从 history 中解析实际生成文件，并复制/登记到 07 images 目录。

当前框架已经记录 output_path，但真实 execute 后还需要补：

```text
history outputs → filename/subfolder/type → /view 下载或本地输出目录 → image_manifest
```

---

### 5. UI 局部重跑按钮真正接接口

现在 UI 有局部重跑入口，但还需要后端 API：

```text
POST /api/image/retry
```

支持：

```json
{"scope":"frame","key":"frame_001"}
{"scope":"appearance","key":"zhang_butou_official_uniform"}
{"scope":"character_lock","key":"charlock_zhang_butou"}
```

---

### 6. 质量检查从结构检查升级为图片检查

当前 07 quality_checker 主要检查结构完整性。

后续可以加：

```text
文件是否存在
图片尺寸是否达标
是否黑图/空图
是否重复图
是否生成失败
```

更高级再加视觉模型评分。

---

### 7. 分镜图锚点策略强化

07D 当前已经记录 anchor_frame_id / continuity_source_frame_id。

后续要把这个真正传给 workflow：

```text
锚点帧：只用场景/造型/道具参考
普通帧：额外输入 anchor frame 或 previous frame
```

---

## 四、推荐 Codex 下一步任务

### 第一批：框架增强

```text
1. 给 07 run_staged.py 增加 --only-stage、--frame-id、--appearance-key、--character-name 参数。
2. 给 stage_runner 增加任务过滤逻辑。
3. 扩展 workflow_mapping 支持 reference_image_slots。
4. 扩展 comfyui_client，支持向 workflow 注入参考图路径。
5. 增加 ComfyUI history 输出解析与图片登记。
```

### 第二批：Web UI 增强

```text
1. 增加 /api/image/retry。
2. 图片阶段卡片的“局部重跑”按钮调用真实接口。
3. 增加 workflow_mapping 预览和校验。
4. 增加每个阶段单独启动按钮：07A / 07B / 07C / 07D。
```

### 第三批：本地测试

```text
1. dry_run 跑 07。
2. 只 execute 07A。
3. 只 execute 07B。
4. 只 execute 07D 的 3 帧。
5. 看 manifest / UI / 图片路径是否完整。
```

---

## 五、最终建议

现阶段不要纠结某一个 ComfyUI 工作流完美不完美。

最重要的是先把这几个能力搭好：

```text
多 workflow 路由
参考图槽位注入
单阶段 / 单任务运行
ComfyUI 结果回收
UI 局部重跑
```

等框架跑通后，再分别精修：

```text
07A 定妆图 workflow
07B 换装 workflow
07D 多参考分镜 workflow
```

这样最稳。