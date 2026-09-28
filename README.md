# AverageFaceGenerator v1.0.0 · 平均脸生成器

本地 Windows 桌面应用，支持 JPG / PNG 单人照、多人合照、平均脸预览、图片与统计导出。无需 Python、GPU 或联网。

## 使用

运行 `dist/AverageFaceGenerator_v1.0.0.exe`。

轻量版为 `AverageFaceGenerator_v1.0.0_lite.exe`，使用 FP16 性别分类模型。应用标题、设置页和 Windows 产品版本均为 `v1.0.0`，Windows 数字文件版本为 `1.0.0.0`。

1. 点击男性／女性／混合单人照或多人合照入口，选择照片或文件夹；文件夹含子文件夹。也可拖入照片或文件夹。只导入一组即可使用；混合单人照和多人合照导入时会用内置模型自动标注性别并分好组（可在“设置”关闭），也可以随时在“样本”页手动修改分组。
2. 勾选样本后可批量修改分组、排除或恢复；支持全选、反选、取消全选。全选和反选作用于当前筛选列表，已勾选项在筛选切换后保留，批量操作作用于所有已勾选项；没有勾选时也可使用鼠标多选。双击查看大图。待确认和排除样本不参与平均。
3. 点击“生成平均脸”。一组样本生成一组结果，两组都有样本时生成两组。
4. 导出 PNG / JPG，或在统计页导出 CSV。

字体优先使用 Windows 微软雅黑 UI，字号 15 px。表格、下拉框、滚动条统一为简洁样式，无滚动条上下箭头。样本列表不显示模糊、偏小、构图等提示；单人照仅显示文件名，合照显示“人脸 n”区分同一张原图中的不同人脸。

“排行”分别显示男性组、女性组最接近和最不接近各自平均脸的样本。生成后打开排行页自动计算，也可点击更新。一组只有一个样本时，最近与最远为同一张。

“比对”上传一张单人照，从全部未排除样本（包括待分组样本）中返回最多 10 个结果。使用本地 SFace 余弦相似度，范围 −1 到 1，越高越相似；不是置信概率或身份确认。结果以样本为单位，不自动合并同一个人的不同照片。修改样本分组、排除状态或重新导入后，旧排行和比对结果清除。

“设置”支持中文、English、日本語和深色模式，切换立即生效且保留当前样本；偏好保存在本机应用数据目录。默认中文、浅色。顶部顺序为平均脸、样本、统计、排行、比对、记录、设置。外观下选择浅色或深色模式；语言框上方单独显示“语言/Language”。“使用说明”移至设置页，平均脸页不再显示附加说明段落。

“自动性别分类”在“设置”页默认开启：导入混合单人照或多人合照时，用内置 SigLIP2 模型逐个标注男性或女性并进入对应分组；男性／女性单人照导入仍沿用手动指定分组。关闭后恢复为全部进入“待确认”手动分组。

没有参考库、跨批次标签传递或人脸识别。男性／女性单人照导入沿用使用者提供的标签；混合照／合照由上述性别分类模型推断性别并进入对应分组，结果可在“样本”页手动修改或改回“待确认”。

照片不上传、不修改原图。当前会话保存在内存中，退出后清空。相同文件内的同一人脸去重，不自动去重不同照片中的同一个人。

## 模型与平均方法

“设置”页可选默认 YuNet + MediaPipe，或外部 InsightFace 几何模型包。切换前需清空样本。

默认 YuNet 检测及五点定位，MediaPipe 提供关键点，选取其中 152 点用于平均形状。高分辨率合照使用重叠分块检测。检测失败、过小或关键点异常的样本会记入处理记录。

五点相似变换统一到 600 × 800 画布，再用三角剖分、分片变形和像素平均生成结果。平均形状的重心坐标只计算一次，每个样本整图重采样，避免逐样本重复构造三角形蒙版。自动校正组内亮度，保留色度及原有颈部、衣领、可用肩部；不做椭圆抠脸，不合成或镜像补全身体。仅累计原图有效像素，没有有效像素的位置为浅灰背景。

导入采用两个后台线程，各自复用几何模型，并安全共享一个性别分类模型；只保留有限的待处理任务。界面批量更新，统计在导入结束后计算。已导入和同一批次中内容相同的文件均在图像解码、模型推理之前跳过；处理失败的文件允许由后续副本重试。

开启“自动性别分类”时，混合／合照导入会在后台使用内置 SigLIP2 性别分类模型，对每个对齐后的人脸做二分类，自动写入男性／女性分组；关闭时不加载该模型，全部进入“待确认”。结果始终可在“样本”页手动修改。

统计为对齐后、形状平均前的均值与标准差。眼距、嘴宽来自五点；脸宽是关键点横向跨度，眉颏高不含额头。单位为画布像素，不是毫米或医学测量。单样本标准差为零。

## 构建

构建机需要 Windows x64、Python 3.12，使用者只需要 EXE。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```
模型权重不提交到 Git。若本机 `models` 已有构建两个版本所需的五个模型文件，可直接执行完整构建；首次克隆或模型缺失时，性别模型需要单独转换一次（构建机联网并安装转换依赖）：
```powershell
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install "transformers==4.50.3" safetensors huggingface_hub onnxscript
.\.venv\Scripts\python.exe tools/prepare_gender_model.py
```
然后按顺序执行：
```powershell
.\.venv\Scripts\python.exe tools/prepare_alternatives.py
.\.venv\Scripts\python.exe tools/prepare_font.py
.\.venv\Scripts\python.exe tools/collect_licenses.py
.\.venv\Scripts\python.exe main.py
```

完整构建：`powershell -ExecutionPolicy Bypass -File .\build.ps1`

lite 轻量版：`powershell -ExecutionPolicy Bypass -File .\build_fp16.ps1`，输出 `dist\AverageFaceGenerator_v1.0.0_lite.exe`（性别模型转为 FP16，模型约 173MB，EXE 约小 150MB；识别结果与 FP32 版本一致，已实测 100% 同标签）。默认构建仍输出 `dist\AverageFaceGenerator_v1.0.0.exe`（FP32 性别模型）。两个版本共用同一份源码与设置布局，只在打包的性别模型精度上有别。

默认打包 YuNet、MediaPipe、SFace 和 SigLIP2 性别分类模型四个模型文件。SFace 仅在首次排行或比对时加载，特征仅在会话内存中缓存，清空样本时删除；性别模型仅在开启自动性别分类且首次导入混合／合照时加载。运行时不下载模型，加载时校验 SHA-256。

两个构建均使用 `assets/AvgFace.ico` 作为 EXE、启动准备窗口及应用窗口图标。构建完成后自动在 EXE 旁生成 `.exe.sha256` 校验文件。

最终仍为单文件 EXE：先由 PyInstaller 生成运行目录，再由 tools/build_launcher.py 封装。启动器使用 Windows 10/11 自带的 .NET Framework 4.x，构建调用系统 csc.exe。首次启动将运行库写入 `%TEMP%/AverageFaceGenerator/runtime-版本标识`，之后复用；每次启动逐文件核对大小与 SHA-256，损坏时重建。缓存只含程序及模型，不含照片或处理结果。清理系统临时文件后下次需重新解压；第一次启动不会和后续启动一样快。

`dist/AvgFaceRuntime` 是构建中间产物，只分发 `dist/AverageFaceGenerator_v1.0.0.exe`（或小体积的 `dist/AverageFaceGenerator_v1.0.0_lite.exe`）即可。修改代码后应重新执行完整 build.ps1，不能只运行 PyInstaller 就将中间程序当作最终单文件发布。

可选研究模型：在“设置”选择已有的、包含 `manifest.json`、`det_500m.onnx`、`2d106det.onnx` 的模型包目录。默认构建不包含这些权重或其下载工具。

## 验证与源码

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

不需要照片数据集的 Windows 原生菜单检查（输出目录必须已存在）：

```powershell
New-Item -ItemType Directory -Force artifacts
.\dist\AverageFaceGenerator_v1.0.0.exe --self-test "$PWD\artifacts\fp32-menus.json" --native-menus
.\dist\AverageFaceGenerator_v1.0.0_lite.exe --self-test "$PWD\artifacts\fp16-menus.json" --native-menus
```

检查使用独立设置文件，验证主题切换、菜单背景及四边实际像素，输出 JSON 和截图。历史照片测试及本次发布验证结果保留在 `TEST_REPORT.md`；测试数据、历史基准/数据集辅助脚本和生成结果已从最小构建目录移除。

源码 MIT；默认模型分别为 MIT / Apache-2.0。依赖运行库各自条款仍适用，包括 PySide6 / Qt 的 LGPLv3。旧 InsightFace 权重仅限非商业研究。详情见 MODEL_LICENSES.md。

准备提交 Git 时，保留源码、测试、构建脚本、`assets` 和 `licenses` 即可；`.gitignore` 已排除虚拟环境、缓存、构建产物、模型权重和本地照片。`models` 中的五个默认构建权重留在本机供再次打包使用，`dist` 仅保留两个 EXE 及其校验文件。`tools` 仅保留构建入口依赖的四个脚本和性别模型转换脚本。清理虚拟环境后，再次构建会按上述步骤重新创建环境并安装依赖。
