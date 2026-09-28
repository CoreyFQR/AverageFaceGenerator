<img width="2559" height="1516" alt="" src="https://github.com/user-attachments/assets/0b46d274-9bff-4929-9f4d-71d3bbe8a7d9" />

# AverageFaceGenerator v1.0.0

A local Windows desktop application for generating average faces. It supports JPG / PNG images, individual portraits, group photos, average-face preview, image export, and statistical data export.

No Python environment, GPU, or Internet connection is required.

## Usage

1. Click the **Male**, **Female**, **Mixed Individual Photos**, or **Group Photos** import option to select photos or folders. Subfolders are also supported. You can also drag and drop photos or folders directly into the application.

   You only need to import one group to start using the application.

   When importing mixed individual photos or group photos, the built-in model automatically detects gender and assigns faces to the corresponding groups. Automatic gender classification can be disabled in **Settings**. You can also manually change the group of any sample at any time on the **Samples** page.

2. Select samples to batch-change their group, exclude them, or restore excluded samples.

   **Select All**, **Invert Selection**, and **Deselect All** are supported. Select All and Invert Selection apply to the currently filtered list, while previously selected samples remain selected when switching filters. Batch operations apply to all selected samples.

   When no checkbox is selected, multiple samples can also be selected using the mouse.

   Double-click a sample to view the full-size image.

   Samples marked as **Pending** or **Excluded** are not used when generating average faces.

3. Click **Generate Average Face**.

   If only one group contains valid samples, one average face will be generated. If both the male and female groups contain valid samples, an average face will be generated for each group.

4. Export the generated average face as **PNG / JPG**, or export statistical data as **CSV** from the Statistics page.

The **Ranking** page separately displays the samples that are most similar and least similar to the average face of their respective male or female group.

The **Comparison** feature allows you to upload a single-person photo and search for the most similar faces among all non-excluded samples, including samples that have not yet been assigned to a group.

Up to **10 results** are returned.

Face similarity is calculated locally using **SFace cosine similarity**, with scores ranging from **−1 to 1**. A higher score indicates greater facial similarity.

The application supports:

- 中文
- English
- 日本語
- Dark Mode

---

# AverageFaceGenerator v1.0.0 · 平均脸生成器

一款本地 Windows 桌面平均脸生成应用，支持 JPG / PNG 图片、单人照、多人合照、平均脸预览、图片导出以及统计数据导出。

无需安装 Python，无需 GPU，也无需联网。

## 使用

1. 点击 **男性**、**女性**、**混合单人照** 或 **多人合照** 入口，选择照片或文件夹进行导入。支持自动读取文件夹中的子文件夹，也可以直接将照片或文件夹拖入程序。

   只需导入其中一组样本即可开始使用。

   导入混合单人照或多人合照时，程序会使用内置模型自动识别性别并分配到对应分组。自动性别分类可以在 **“设置”** 中关闭，也可以随时在 **“样本”** 页面手动修改任意样本的分组。

2. 勾选样本后，可以批量修改分组、排除样本或恢复已排除样本。

   支持 **全选、反选和取消全选**。全选和反选仅作用于当前筛选列表；切换筛选条件后，已经勾选的样本仍会保持选中状态。批量操作会作用于所有已勾选的样本。

   没有使用复选框时，也可以通过鼠标进行多选。

   双击样本可以查看大图。

   标记为 **待确认** 或 **已排除** 的样本不会参与平均脸生成。

3. 点击 **“生成平均脸”**。

   如果只有一组存在有效样本，则生成一组平均脸；如果男性组和女性组均存在有效样本，则分别生成两组平均脸。

4. 可以将生成结果导出为 **PNG / JPG** 图片，也可以在统计页面将统计数据导出为 **CSV** 文件。

**“排行”** 页面会分别显示男性组和女性组中，与各自平均脸 **最接近** 和 **最不接近** 的样本。

**“比对”** 功能支持上传一张单人照片，并从全部未排除样本中搜索与其最相似的人脸，包括尚未完成分组的待分组样本。最多返回 **10 个结果**。

相似度使用本地 **SFace 余弦相似度** 计算，取值范围为 **−1 到 1**，数值越高表示人脸越相似。
