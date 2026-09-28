from __future__ import annotations

import csv
import traceback
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer
from PySide6.QtGui import QImage, QPixmap, QIcon, QFontDatabase, QFont
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QFileDialog, QComboBox, QProgressBar,
    QListWidget, QListWidgetItem, QAbstractItemView, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QSplitter, QPlainTextEdit, QDialog, QMenu, QStyledItemDelegate, QListView, QCheckBox)

from .widgets import ComboBox as QComboBox, RoundedMenu as QMenu
from .features_ui import Features
from .i18n import tr, set_language
from . import DISPLAY_VERSION

from .common import Cancelled, GROUP_NAMES, METRICS, resource_dir, photo_paths

STYLE = """
QWidget { background: #f3f5f9; color: #202a3a; font-family: 'Microsoft YaHei UI', 'Noto Sans SC'; font-size: 15px; }
QLabel#preview { background: #f1f4f9; color: #536174; border-radius: 12px; }
QMainWindow { background: #f3f5f9; }
QFrame#card { background: white; border: 1px solid #e1e6ee; border-radius: 14px; }
QFrame#card QLabel { background: transparent; }
QLabel#title { font-size: 25px; font-weight: 700; }
QLabel#section { font-size: 18px; font-weight: 600; }
QLabel#muted { color: #536174; }
QLabel#tag { color: #407260; background: #e5f2eb; padding: 7px 12px; border-radius: 10px; }
QPushButton { background: white; border: 1px solid #dce2ec; border-radius: 8px; padding: 9px 14px; }
QPushButton:hover { border-color: #5878ee; background: #f1f4ff; }
QPushButton:disabled { color: #a0a8b5; background: #f2f4f7; border-color: #e5e8ed; }
QPushButton#primary { background: #4968e8; color: white; border: none; font-weight: 600; }
QPushButton#primary:hover { background: #3d5bd6; }
QPushButton#primary:disabled { background: #aebbe9; }
QComboBox { background: white; border: 1px solid #e1e6ee; border-radius: 7px; padding: 7px; }
QListWidget, QTableWidget, QPlainTextEdit { background: white; border: 1px solid #e1e6ee; border-radius: 9px; }
QListWidget::item { padding: 8px; border-radius: 6px; }
QListWidget::item:selected { background: #e9eeff; color: #304aa3; }
QHeaderView::section { background: #f5f7fc; border: none; padding: 10px; color: #536174; }
QTabWidget::pane { border: none; }
QTabBar::tab { padding: 12px 12px; color: #536174; border-bottom: 3px solid transparent; }
QTabBar::tab:selected { color: #4968e8; border-bottom: 3px solid #4968e8; }
QProgressBar { background: #e5e9f2; border: none; border-radius: 4px; max-height: 7px; }
QProgressBar::chunk { background: #6b83ec; border-radius: 4px; }
QCheckBox { background: transparent; spacing: 8px; }
QCheckBox::indicator { width: 20px; height: 20px; border: 1px solid #aeb9ca; border-radius: 6px; background: white; }
QCheckBox::indicator:checked { background: #4968e8; border-color: #4968e8; image: url("@ASSETS@/check.svg"); }
QComboBox { padding: 9px 32px 9px 12px; min-height: 20px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 30px; border: none; }
QComboBox::down-arrow { image: url("@ASSETS@/chevron-down.svg"); width: 16px; height: 16px; }
QComboBox QAbstractItemView { background: white; border: 1px solid #e1e6ee; border-radius: 8px; padding: 5px; outline: none; selection-background-color: #edf1ff; selection-color: #304aa3; }
QComboBox QAbstractItemView::item { min-height: 34px; padding: 4px 10px; border-radius: 5px; }
QPushButton::menu-indicator { image: url("@ASSETS@/chevron-down.svg"); width: 14px; height: 14px; subcontrol-origin: padding; subcontrol-position: right center; right: 8px; }
QMenu { background: white; border: 1px solid transparent; padding: 6px; }
QMenu::item { padding: 10px 28px 10px 16px; border-radius: 6px; }
QMenu::item:selected { background: #edf1ff; color: #304aa3; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; border: none; }
QScrollBar::handle:vertical { background: #c3cbd9; border-radius: 3px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: #92a1b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; background: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; border: none; }
QScrollBar::handle:horizontal { background: #c3cbd9; border-radius: 3px; min-width: 32px; }
QScrollBar::handle:horizontal:hover { background: #92a1b8; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; border: none; background: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QScrollBar::up-arrow, QScrollBar::down-arrow, QScrollBar::left-arrow, QScrollBar::right-arrow { width: 0px; height: 0px; image: none; }
QTableWidget { alternate-background-color: #f8faff; selection-background-color: #edf1ff; selection-color: #202a3a; gridline-color: transparent; outline: none; }
QTableWidget::item { padding: 10px 14px; border-bottom: 1px solid #eef1f7; }
QTableCornerButton::section { background: #f5f7fc; border: none; }
QListWidget { outline: none; }
QListWidget::indicator { width: 18px; height: 18px; border: 1px solid #aeb9ca; border-radius: 5px; background: white; }
QListWidget::indicator:hover { border-color: #4968e8; }
QListWidget::indicator:checked { background: #4968e8; border-color: #4968e8; image: url("@ASSETS@/check.svg"); }
QToolTip { background: #202a3a; color: white; border: none; padding: 6px 10px; }
"""


def pixmap(bgr):
    import cv2
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h,w = rgb.shape[:2]
    return QPixmap.fromImage(QImage(rgb.data,w,h,w*3,QImage.Format.Format_RGB888).copy())


def label(text, role=None):
    item = QLabel(text)
    if role:
        item.setObjectName(role)
    return item


class Preview(QLabel):
    def __init__(self):
        super().__init__(tr('等待生成'))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(220,220)
        self.original = None
        self.setObjectName("preview")

    def show_image(self, img):
        self.original = pixmap(img) if img is not None else None
        self.redraw()

    def redraw(self):
        if self.original is not None:
            self.setPixmap(self.original.scaled(self.size()-QSize(12,12), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.setPixmap(QPixmap())
            self.setText(tr('等待生成'))

    def resizeEvent(self,event):
        self.redraw()
        super().resizeEvent(event)


class Worker(QThread):
    progress = Signal(int,str)
    batch = Signal(object)
    result = Signal(object)
    note = Signal(str)
    error = Signal(str)

    def __init__(self, task, **kwargs):
        super().__init__()
        self.task, self.kwargs = task, kwargs

    def run(self):
        own_session = None
        try:
            if self.task == "import":
                self.progress.emit(0,tr('正在导入照片…'))
                from .importer import ImportSession
                session=self.kwargs.get('session')
                if session is None:session=own_session=ImportSession()
                paths=list(photo_paths(self.kwargs['paths']))
                if not paths:
                    self.note.emit(tr('未找到 PNG / JPG 照片')); return
                buffered=[]; last_update=time.monotonic()
                for i,(path,(faces,notes)) in enumerate(session.iterate(paths,self.kwargs['mode'],self.kwargs['group_photo'],
                        self.isInterruptionRequested,self.kwargs.get('engine_options',{}),self.kwargs.get('known',set()))):
                    buffered.extend(faces)
                    for note in notes:self.note.emit(f"{Path(path).name}：{note}")
                    if time.monotonic()-last_update>=.15 or i+1==len(paths):
                        if buffered:self.batch.emit(buffered); buffered=[]
                        self.progress.emit(round((i+1)/len(paths)*100),tr('已处理 {0} / {1} 张照片').format(i+1,len(paths)))
                        last_update=time.monotonic()
                if buffered:self.batch.emit(buffered)
            elif self.task in ('rank','compare'):
                model=self.kwargs['similarity']
                progress=lambda n,t:self.progress.emit(round(n/max(t,1)*100),tr('正在计算相似度 · {0}/{1}').format(n,t))
                if self.task=='rank':
                    self.result.emit(model.rank(self.kwargs['faces'],self.kwargs['averages'],self.isInterruptionRequested,progress))
                else:
                    from .engine import Engine
                    engine=Engine(**self.kwargs['engine_options'])
                    try:
                        faces,notes=engine.process(self.kwargs['path'],cancelled=self.isInterruptionRequested)
                        if len(faces)!=1:raise ValueError(tr('请上传仅包含一张清晰人脸的照片。'))
                        matches=model.compare(faces[0],self.kwargs['faces'],self.isInterruptionRequested,progress)
                        self.result.emit((faces[0],matches))
                    finally:engine.close()
            else:
                from .engine import average
                faces = self.kwargs["faces"]
                results = {}
                groups = [(g,[f for f in faces if f.enabled and f.group==g]) for g in ("male","female")]
                total = sum(len(fs) for _,fs in groups)
                done = 0
                for group,items in groups:
                    if items:
                        results[group] = average(items,self.kwargs["normalize"],self.isInterruptionRequested,
                            lambda n,t: self.progress.emit(round((done+n)/total*100),tr('正在生成{0}平均脸 · {1}/{2}').format(tr(GROUP_NAMES[group]),n,t)))
                        done += len(items)
                self.result.emit(results)
        except Cancelled:
            self.note.emit(tr('操作已取消。已导入的样本仍然保留。'))
        except Exception:
            self.error.emit(traceback.format_exc())
        finally:
            if own_session:own_session.close()


class Window(Features, QMainWindow):
    def __init__(self):
        super().__init__()
        set_language("zh")
        self.setWindowTitle(tr('平均脸生成器 · Average Face Generator'))
        self.resize(1260,880)
        self.setMinimumSize(1030,740)
        self.faces, self.results, self.ids = [], {}, set()
        self.worker = None
        self.busy = False
        self.research_dir = None
        self.import_session = None
        self.checked_ids = set()
        self.thumbnail_cache = {}
        self.setAcceptDrops(True)
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(26,22,26,18); layout.setSpacing(16)
        header = QHBoxLayout()
        titles = QVBoxLayout(); titles.addWidget(label(tr('平均脸生成器'), "title"))
        header.addLayout(titles); header.addStretch()
        layout.addLayout(header)
        body = QSplitter(Qt.Orientation.Horizontal); layout.addWidget(body,1)
        sidebar = QFrame(); sidebar.setObjectName("card"); sidebar.setMinimumWidth(260); sidebar.setMaximumWidth(330)
        side = QVBoxLayout(sidebar); side.setContentsMargins(20,22,20,20); side.setSpacing(12)
        side.addWidget(label(tr('导入照片'), "section"))
        self.actions = []
        for text,mode,group in [(tr('＋  男性单人照'),"male",False),(tr('＋  女性单人照'),"female",False),(tr('＋  混合单人照'),"auto",False),(tr('＋  多人合照'),"auto",True)]:
            btn=QPushButton(text); menu=QMenu(btn)
            menu.addAction(tr('选择照片…'),lambda checked=False,m=mode,g=group:self.choose_files(m,g))
            menu.addAction(tr('选择文件夹…'),lambda checked=False,m=mode,g=group:self.choose_folder(m,g))
            btn.setMenu(menu); side.addWidget(btn); self.actions.append(btn)
        side.addSpacing(10); side.addWidget(label(tr('生成'), "section"))
        self.counts = label(tr('尚未导入样本'), "muted"); self.counts.setWordWrap(True); side.addWidget(self.counts)
        self.generate = QPushButton(tr('生成平均脸')); self.generate.setObjectName("primary"); self.generate.clicked.connect(self.start_average); side.addWidget(self.generate)
        self.clear = QPushButton(tr('清空当前样本')); self.clear.clicked.connect(self.clear_all); side.addWidget(self.clear); self.actions.append(self.clear)
        side.addStretch()
        body.addWidget(sidebar)
        right = QWidget(); right_layout = QVBoxLayout(right); right_layout.setContentsMargins(16,0,0,0)
        self.tabs = QTabWidget(); right_layout.addWidget(self.tabs)
        results_page = QWidget(); results_layout = QVBoxLayout(results_page); results_layout.setContentsMargins(0,12,0,0)
        cards = QHBoxLayout(); self.previews={}; self.export_buttons={}; self.result_labels={}; self.result_cards={}
        for group in ("male","female"):
            card = QFrame(); card.setObjectName("card"); cl = QVBoxLayout(card); cl.setContentsMargins(18,18,18,18)
            cl.addWidget(label(tr(tr('男性平均脸') if group=="male" else tr('女性平均脸')), "section"))
            info = label(tr('等待生成'), "muted"); cl.addWidget(info); self.result_labels[group]=info
            preview = Preview(); cl.addWidget(preview,1); self.previews[group]=preview
            export = QPushButton(tr('导出图片…')); export.setEnabled(False); export.clicked.connect(lambda checked=False,g=group:self.export_image(g)); cl.addWidget(export); self.export_buttons[group]=export
            cards.addWidget(card); self.result_cards[group]=card
        results_layout.addLayout(cards,1)
        self.empty_result=label(tr('导入照片开始')); self.empty_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        results_layout.addWidget(self.empty_result,1)
        self.tabs.addTab(results_page,tr('平均脸'))
        samples = QWidget(); sl = QVBoxLayout(samples)
        toolbar = QHBoxLayout(); self.filter = QComboBox()
        for key,name in [("all",tr('全部样本')),*GROUP_NAMES.items()]: self.filter.addItem(name,key)
        self.filter.currentIndexChanged.connect(self.rebuild_list); toolbar.addWidget(self.filter)
        for title,group in [(tr('设为男性'),"male"),(tr('设为女性'),"female"),(tr('待确认'),"review"),(tr('排除 / 恢复'),None)]:
            b=QPushButton(title); b.clicked.connect(lambda checked=False,g=group:self.change_selected(g)); toolbar.addWidget(b); self.actions.append(b)
        sl.addLayout(toolbar)
        self.list = QListWidget(); self.list.setIconSize(QSize(75,100)); self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection); self.list.itemDoubleClicked.connect(self.inspect_face); self.list.itemChanged.connect(self.check_changed)
        self.list.setUniformItemSizes(True); self.list.setLayoutMode(QListView.LayoutMode.Batched); self.list.setBatchSize(100); sl.addWidget(self.list)
        checks=QHBoxLayout()
        for title,action in ((tr('全选'),'all'),(tr('反选'),'invert'),(tr('取消全选'),'none')):
            button=QPushButton(title); button.clicked.connect(lambda checked=False,a=action:self.check_visible(a)); checks.addWidget(button)
        self.checked_label=label(tr('已勾选 0'), "muted"); checks.addStretch(); checks.addWidget(self.checked_label); sl.addLayout(checks)
        self.tabs.addTab(samples,tr('样本'))
        stats_page=QWidget(); st=QVBoxLayout(stats_page)
        self.table=QTableWidget(0,3); self.table.setHorizontalHeaderLabels([tr('参数'),tr('男性组'),tr('女性组')]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.table.verticalHeader().hide(); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.setShowGrid(False); self.table.setAlternatingRowColors(True); self.table.verticalHeader().setDefaultSectionSize(48); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); st.addWidget(self.table)
        note=label(tr('均值 ± 标准差 · 长度单位：像素'), "muted"); st.addWidget(note)
        self.table.setToolTip(tr('统计基于对齐画布，不是毫米。眉颏高不含额头。'))
        self.csv_button=QPushButton(tr('导出统计…')); self.csv_button.clicked.connect(self.export_csv); st.addWidget(self.csv_button)
        self.tabs.addTab(stats_page,tr('统计'))
        self.logs=QPlainTextEdit(); self.logs.setReadOnly(True); self.logs.setPlaceholderText(tr('暂无处理记录')); self.tabs.addTab(self.logs,tr('记录'))
        settings=QWidget(); settings_layout=QVBoxLayout(settings); settings_layout.setSpacing(16)
        settings_layout.addWidget(label(tr('自动性别分类'), "section"))
        self.auto_gender_check=QCheckBox(tr('导入混合单人照或多人合照时自动标注性别'))
        self.auto_gender_check.setChecked(True)
        self.auto_gender_check.toggled.connect(self.save_preferences)
        self.auto_gender_check.setToolTip(tr('男性/女性单人照导入仍保持手动指定分组。'))
        settings_layout.addWidget(self.auto_gender_check)
        settings_layout.addWidget(label(tr('人脸处理模型'), "section"))
        self.backend_choice=QComboBox()
        self.backend_choice.addItem(tr('YuNet + MediaPipe（默认）'), "open")
        self.backend_choice.addItem(tr('InsightFace（非商业研究）'), "insightface")
        settings_layout.addWidget(self.backend_choice)
        self.model_folder_button=QPushButton(tr('选择 InsightFace 模型包文件夹…'))
        self.model_folder_button.clicked.connect(self.choose_model_folder); settings_layout.addWidget(self.model_folder_button)
        self.backend_choice.setToolTip(tr('YuNet：MIT；MediaPipe：Apache-2.0。切换模型前请清空样本。'))
        self.about_button = QPushButton(tr('使用说明')); self.about_button.clicked.connect(self.about)
        settings_layout.addWidget(self.about_button)
        settings_layout.addWidget(label(f'AverageFaceGenerator {DISPLAY_VERSION}', 'muted'))
        settings_layout.addStretch(); self.tabs.addTab(settings,tr('设置'))
        body.addWidget(right); body.setStretchFactor(1,1)
        status=QHBoxLayout(); self.status=label(tr('就绪'), "muted"); status.addWidget(self.status,1)
        self.cancel=QPushButton(tr('取消处理')); self.cancel.clicked.connect(self.cancel_work); self.cancel.setVisible(False); status.addWidget(self.cancel); layout.addLayout(status)
        self.progress=QProgressBar(); self.progress.setTextVisible(False); self.progress.setValue(0); layout.addWidget(self.progress)
        self.build_features(results_layout,settings_layout)
        self.capture_translations()
        self.load_preferences()
        self.update_counts()
        for combo in (self.filter,self.backend_choice):combo.setItemDelegate(QStyledItemDelegate(combo))

    def choose_files(self,mode,group):
        paths,_=QFileDialog.getOpenFileNames(self,tr('选择照片'), "", tr('图片 (*.png *.jpg *.jpeg)'))
        if paths:self.start_import(paths,mode,group)

    def choose_folder(self,mode,group):
        folder=QFileDialog.getExistingDirectory(self,tr('选择文件夹'))
        if folder:self.start_import([folder],mode,group)

    def start_import(self,paths,mode="auto",group=False):
        if self.busy:return
        backend=self.backend_choice.currentData()
        if backend=="insightface" and not self.research_dir:
            QMessageBox.information(self,tr('请选择模型包'),tr('在「设置」选择包含 manifest.json、det_500m.onnx 和 2d106det.onnx 的模型包文件夹。'))
            return
        self.invalidate()
        if self.import_session is None:
            from .importer import ImportSession
            self.import_session=ImportSession()
        options=dict(backend=backend,auto_gender=self.auto_gender_check.isChecked())
        if backend=="insightface":options['model_dir']=self.research_dir
        self.worker=Worker("import",paths=list(dict.fromkeys(paths)),mode=mode,group_photo=group,engine_options=options,session=self.import_session,known={f.id.split(":")[0] for f in self.faces})
        self.worker.batch.connect(self.add_faces)
        self.start_worker()

    def start_worker(self):
        self.busy=True
        self.backend_choice.setEnabled(False); self.model_folder_button.setEnabled(False)
        for b in self.actions:b.setEnabled(False)
        self.generate.setEnabled(False); self.cancel.setVisible(True); self.cancel.setEnabled(True)
        self.worker.progress.connect(self.on_progress); self.worker.note.connect(self.logs.appendPlainText)
        self.worker.error.connect(self.show_error); self.worker.finished.connect(self.finished)
        self.worker.start()

    def on_progress(self,value,text):
        self.progress.setValue(value); self.status.setText(text)

    def cancel_work(self):
        if self.worker:self.worker.requestInterruption(); self.cancel.setEnabled(False); self.status.setText(tr('正在结束当前步骤…'))

    def finished(self):
        self.busy=False
        for b in self.actions:b.setEnabled(True)
        self.cancel.setVisible(False)
        self.rebuild_list(); self.update_counts()
        self.status.setText(tr('处理完成'))
        self.worker.deleteLater(); self.worker=None

    def add_faces(self,faces):
        duplicates=0
        for face in faces:
            if face.id in self.ids:duplicates+=1;continue
            self.ids.add(face.id); self.faces.append(face)
        if duplicates:self.logs.appendPlainText(tr('跳过 {0} 张已导入的人脸（相同文件内容）。').format(duplicates))
        self.update_counts(refresh_stats=not self.busy)

    def update_counts(self,refresh_stats=True):
        self.backend_choice.setEnabled(not self.busy and not self.faces)
        self.model_folder_button.setEnabled(not self.busy and not self.faces)
        count={g:sum(f.enabled and f.group==g for f in self.faces) for g in GROUP_NAMES}
        self.counts.setText(tr('男性 {0}   ·   女性 {1}\n待确认 {2}   ·   共 {3} 张人脸').format(count['male'],count['female'],count['review'],len(self.faces)))
        for group,card in self.result_cards.items():card.setVisible(count[group]>0)
        self.empty_result.setVisible(count["male"]+count["female"]==0)
        self.empty_result.setText(tr('请先在样本中确认分组') if self.faces else tr('导入照片开始'))
        self.generate.setEnabled(not self.busy and count['male']+count['female']>0)
        self.csv_button.setEnabled(bool(self.faces))
        if hasattr(self,"rank_button"):
            self.rank_button.setEnabled(not self.busy and bool(self.results))
            self.compare_button.setEnabled(not self.busy and any(f.enabled for f in self.faces))
        if not refresh_stats:return
        if self.faces:
            from .engine import statistics
            stats=statistics(self.faces)
        else:stats={g:{"count":0,"metrics":{}} for g in ("male","female")}
        self.table.setRowCount(len(METRICS)+1)
        self.table.setItem(0,0,QTableWidgetItem(tr('参与平均的样本数')))
        for col,g in enumerate(("male","female"),1):
            item=QTableWidgetItem(str(stats[g]['count'])); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(0,col,item)
        for row,(key,title) in enumerate(METRICS.items(),1):
            self.table.setItem(row,0,QTableWidgetItem(tr(title)))
            for col,g in enumerate(("male","female"),1):
                v=stats[g]["metrics"].get(key)
                text=f"{v['mean']:.3f} ± {v['std']:.3f}" if v else "—"
                item=QTableWidgetItem(text); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(row,col,item)

    def rebuild_list(self):
        from PySide6.QtGui import QImage
        self.list.blockSignals(True); self.list.setUpdatesEnabled(False)
        self.list.clear(); group=self.filter.currentData()
        for i,f in enumerate(self.faces):
            if group!="all" and f.group!=group:continue
            state=tr(GROUP_NAMES[f.group]) if f.enabled else tr('已排除')
            suffix=tr(' · 人脸 {0}').format(f.index) if f.group_photo else ""
            icon=self.thumbnail_cache.get(f.id)
            if icon is None:
                # QImage scales only the thumbnail, without an extra full-size RGB copy.
                h,w=f.image.shape[:2]
                qimage=QImage(f.image.data,w,h,int(f.image.strides[0]),QImage.Format.Format_BGR888)
                icon=QIcon(QPixmap.fromImage(qimage.scaled(75,100,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)))
                self.thumbnail_cache[f.id]=icon
            item=QListWidgetItem(icon,f"{Path(f.source).name}{suffix}\n{state}")
            item.setData(Qt.ItemDataRole.UserRole,i)
            item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if f.id in self.checked_ids else Qt.CheckState.Unchecked)
            self.list.addItem(item)
        self.list.blockSignals(False); self.list.setUpdatesEnabled(True)
        self.checked_label.setText(tr('已勾选 {0}').format(len(self.checked_ids)))

    def check_changed(self,item):
        face=self.faces[item.data(Qt.ItemDataRole.UserRole)]
        if item.checkState()==Qt.CheckState.Checked:self.checked_ids.add(face.id)
        else:self.checked_ids.discard(face.id)
        self.checked_label.setText(tr('已勾选 {0}').format(len(self.checked_ids)))

    def check_visible(self,action):
        if action=='none':self.checked_ids.clear()
        self.list.blockSignals(True)
        for n in range(self.list.count()):
            item=self.list.item(n); face=self.faces[item.data(Qt.ItemDataRole.UserRole)]
            if action=='all':self.checked_ids.add(face.id)
            elif action=='invert':
                if face.id in self.checked_ids:self.checked_ids.remove(face.id)
                else:self.checked_ids.add(face.id)
            item.setCheckState(Qt.CheckState.Checked if face.id in self.checked_ids else Qt.CheckState.Unchecked)
        self.list.blockSignals(False)
        self.checked_label.setText(tr('已勾选 {0}').format(len(self.checked_ids)))

    def change_selected(self,group):
        if self.busy:return
        indices=[i for i,f in enumerate(self.faces) if f.id in self.checked_ids] if self.checked_ids else [item.data(Qt.ItemDataRole.UserRole) for item in self.list.selectedItems()]
        if not indices:return
        for i in indices:
            face=self.faces[i]
            if group:face.group=group; face.label_source=tr('人工修改标签')
            else:face.enabled=not face.enabled
        self.invalidate(); self.rebuild_list(); self.update_counts()

    def invalidate(self,*args):
        self.results={}
        self.invalidate_features()
        if hasattr(self,"previews"):
            for g,p in self.previews.items():p.show_image(None); self.export_buttons[g].setEnabled(False); self.result_labels[g].setText(tr('等待生成'))

    def start_average(self):
        if self.busy:return
        self.invalidate()
        self.worker=Worker("average",faces=list(self.faces),normalize=True)
        self.worker.result.connect(self.show_results); self.tabs.setCurrentIndex(0); self.start_worker()

    def show_results(self,results):
        self.results=results
        for g,(img,points) in results.items():
            self.previews[g].show_image(img); self.export_buttons[g].setEnabled(True)
            n=sum(f.enabled and f.group==g for f in self.faces)
            self.result_labels[g].setText(tr('{0} 张照片').format(n))

    def export_image(self,group):
        if group not in self.results:return
        path,_=QFileDialog.getSaveFileName(self,tr('导出平均脸'),tr('{0}平均脸.png').format(tr(GROUP_NAMES[group])),"PNG (*.png);;JPEG (*.jpg)")
        if path:
            try:
                from .engine import write_image
                if not Path(path).suffix:path += ".png"
                write_image(path,self.results[group][0]); self.status.setText(tr('已导出：{0}').format(path))
            except Exception as e:QMessageBox.warning(self,tr('导出失败'),str(e))

    def export_csv(self):
        path,_=QFileDialog.getSaveFileName(self,tr('导出统计'),tr('人脸统计.csv'),"CSV (*.csv)")
        if not path:return
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as file:
                writer=csv.writer(file); writer.writerow([tr('文件'),tr('人脸序号'),tr('分组'),tr('参与平均'),tr('标签来源'),tr('关键点模型'),*[tr(v) for v in METRICS.values()]])
                for f in self.faces:
                    name=Path(f.source).name
                    if name.startswith(("=","+","-","@")):name="'"+name
                    writer.writerow([name,f.index,tr(GROUP_NAMES[f.group]),f.enabled and f.group!="review",tr(f.label_source),f.backend,*[f.metrics[k] for k in METRICS]])
            self.status.setText(tr('已导出：{0}').format(path))
        except Exception as e:QMessageBox.warning(self,tr('导出失败'),str(e))

    def inspect_face(self,item):
        import cv2
        f=self.faces[item.data(Qt.ItemDataRole.UserRole)]; dialog=QDialog(self); dialog.setWindowTitle(Path(f.source).name+(tr(' · 人脸 {0}').format(f.index) if f.group_photo else ""))
        lay=QVBoxLayout(dialog); pictures=QHBoxLayout(); pic=QLabel(); img=f.image.copy()
        for p in f.points:cv2.circle(img,tuple(p.astype(int)),1,(100,230,110),-1)
        pic.setPixmap(pixmap(img).scaled(420,560,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)); pictures.addWidget(pic)
        lay.addLayout(pictures); lay.addWidget(label(tr(GROUP_NAMES[f.group]))); dialog.exec()

    def clear_all(self):
        if self.faces and QMessageBox.question(self,tr('清空样本'),tr('清空本次导入与结果？原始照片不会被修改。'))!=QMessageBox.StandardButton.Yes:return
        if self.similarity:self.similarity.clear()
        self.faces=[]; self.ids=set(); self.checked_ids.clear(); self.thumbnail_cache.clear(); self.invalidate(); self.rebuild_list(); self.update_counts(); self.logs.clear(); self.progress.setValue(0)

    def show_error(self,text):
        self.logs.appendPlainText(text); QMessageBox.warning(self,tr('处理失败'),text.splitlines()[-1])

    def about(self):
        QMessageBox.information(self,tr('使用说明'), tr('导入照片 → 检查样本 → 生成平均脸 → 导出。\n混合照和合照请在样本页手动分组。\n排行比较组内样本与平均脸；比对搜索未排除的样本。\n相似度不是身份确认概率。\n\n照片和相似度特征只保存在本次会话内存中。\n模型：YuNet、MediaPipe、SFace。详细授权见 MODEL_LICENSES.md。'))

    def choose_model_folder(self):
        folder=QFileDialog.getExistingDirectory(self,tr('选择 InsightFace 模型包'))
        if folder:
            self.research_dir=folder; self.model_folder_button.setText(tr('模型包：{0}').format(Path(folder).name))

    def dragEnterEvent(self,event):
        if not self.busy and event.mimeData().hasUrls():event.acceptProposedAction()

    def dropEvent(self,event):
        paths=[u.toLocalFile() for u in event.mimeData().urls() if Path(u.toLocalFile()).is_dir() or Path(u.toLocalFile()).suffix.lower() in (".png",".jpg",".jpeg")]
        if paths:
            from PySide6.QtWidgets import QInputDialog
            choice,ok=QInputDialog.getItem(self,tr('导入照片'),tr('照片类型'),[tr('混合单人照'),tr('多人合照'),tr('男性单人照'),tr('女性单人照')],0,False)
            if ok:self.start_import(paths,{tr('男性单人照'):"male",tr('女性单人照'):"female"}.get(choice,"auto"),choice==tr('多人合照'))

    def closeEvent(self,event):
        if self.busy:
            self.cancel_work(); event.ignore(); self.status.setText(tr('正在取消处理，结束后可关闭窗口。'))
        else:
            if self.import_session:self.import_session.close(); self.import_session=None
            event.accept()


def configure_app(app):
    app.setApplicationVersion(DISPLAY_VERSION)
    app.setProperty('avgfaceDarkTheme',False)
    app.setWindowIcon(QIcon(str(resource_dir()/"assets"/"AvgFace.ico")))
    if "Microsoft YaHei UI" in QFontDatabase.families():
        app.setFont(QFont("Microsoft YaHei UI",11))
    else:
        font_path=resource_dir()/"assets"/"NotoSansSC.ttf"
        if font_path.exists():
            font_id=QFontDatabase.addApplicationFont(str(font_path))
            families=QFontDatabase.applicationFontFamilies(font_id)
            if families:app.setFont(QFont(families[0],11))
    app.setStyle("Fusion"); app.setStyleSheet(STYLE.replace("@ASSETS@",(resource_dir()/"assets").as_posix()))


def main():
    app=QApplication.instance() or QApplication([])
    configure_app(app)
    window=Window(); window.show()
    import sys
    if '--startup-test' in sys.argv:
        def ready():
            import json
            output=Path(sys.argv[sys.argv.index('--startup-test')+1])
            output.write_text(json.dumps({'window_ready':True,'inference_loaded':'avgface.engine' in sys.modules}),encoding='utf-8')
            window.close(); app.quit()
        QTimer.singleShot(100,ready)
    return app.exec()
