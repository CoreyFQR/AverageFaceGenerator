# Third-party notices

InsightFace model conventions and inference design:
https://github.com/deepinsight/insightface/tree/v0.7/python-package/insightface/model_zoo
Copyright (c) 2020 InsightFace — MIT code license (see InsightFace-MIT.txt).

The bundled det_500m.onnx, 2d106det.onnx, genderage.onnx are from official buffalo_s.zip:
https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip
Weights and their training data are restricted to non-commercial research.
https://github.com/deepinsight/insightface/tree/master/model_zoo
The application does not include or use an identity recognition model.

Runtime dependencies: Python (PSF), PySide6 / Shiboken / Qt (LGPLv3 and associated notices),
NumPy (BSD), SciPy (BSD and bundled library notices), Pillow (MIT-CMU),
OpenCV (Apache-2.0 and bundled library notices), ONNX Runtime (MIT).
Installed distributions' license texts are copied here by tools/collect_licenses.py before release builds.

The bundled realistic_gender.onnx is an ONNX conversion of prithivMLmods/Realistic-Gender-Classification
(a SigLIP2 image-classification fine-tune, Apache-2.0), used only for the optional auto gender labeling:
https://huggingface.co/prithivMLmods/Realistic-Gender-Classification
Base model google/siglip2-base-patch16-224 is also Apache-2.0.

The source and build recipe are provided alongside this program so users may modify the application,
replace dynamically loaded LGPL libraries, and rebuild. No restriction on reverse engineering for
debugging modifications to LGPL libraries is imposed.
