# 模型和发布授权

## 当前默认版本

|组件|用途|上游许可|
|---|---|---|
|YuNet 2023mar|人脸检测、五点定位|MIT|
|MediaPipe Face Landmarker float16 v1|关键点定位，用于对齐和平均形状|Apache-2.0|
|OpenCV SFace 2021dec|排行与照片相似度比对|Apache-2.0|
|Realistic-Gender-Classification (SigLIP2 base)|混合／合照导入时的可选性别标注|Apache-2.0|

默认 EXE 内置这四个模型文件。SFace 只用于用户主动请求的排行和比对，不用于身份识别或跨批次标签传递。性别分类模型只用于“自动性别分类”开启时对混合照／合照进行二分类标注，可在“设置”关闭；它不识别个人身份。平均脸由几何变换和像素平均生成，不重新训练模型。固定 SHA-256 见 avgface/models.py。

上游许可证和模型卡：

- https://github.com/opencv/opencv_zoo/blob/main/models/face_detection_yunet/LICENSE
- https://github.com/opencv/opencv_zoo/blob/main/models/face_recognition_sface/LICENSE
- https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Face%20Mesh%20V2.pdf
- https://storage.googleapis.com/mediapipe-assets/MediaPipe%20BlazeFace%20Model%20Card%20(Short%20Range).pdf
- https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Blendshape%20V2.pdf （任务包附带，未启用该输出）
- https://huggingface.co/prithivMLmods/Realistic-Gender-Classification （性别分类模型；其底座 SigLIP 2 也遵循 Apache-2.0，参见 https://huggingface.co/google/siglip2-base-patch16-224）

MIT / Apache-2.0 允许商业用途，仍需保留版权、许可证和适用通知。照片自身的使用授权不由模型许可证提供。

## 可选外部 InsightFace 模型

`det_500m.onnx`（SCRFD 检测）和 `2d106det.onnx`（106 点定位）作为独立外部模型包提供。默认 EXE 与源码压缩包不包含这些权重。

InsightFace 代码为 MIT，但官方预训练权重仅限非商业研究。免费或开源不自动解除权重限制，商业用途需另行获得相应授权。

官方依据：https://github.com/deepinsight/insightface#license

旧版曾使用 genderage 属性分类模型，当前版本不再使用或打包它。

## GitHub 与二进制发布

本项目自己的源码按根目录 MIT LICENSE 发布，可以开源到 GitHub。测试照片、导出图片和模型权重不包含在源码压缩包中。

第三方运行库保留各自许可。尤其 PySide6 / Qt 的 LGPLv3：应保留授权文件，允许修改、调试及重新链接，并依照许可证提供所需对应源码／获取方式。单文件打包不会消除这些义务。

Qt / PySide6 6.8.3 对应源码入口：

- https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/
- https://download.qt.io/archive/qt/6.8/6.8.3/single/
- https://doc.qt.io/qtforpython-6/licenses.html

许可证在 licenses/，也内嵌于 EXE；构建步骤见 README.md。公开发行二进制前，发行方需要落实第三方依赖的对应源码提供义务。
