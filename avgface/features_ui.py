"""Ranking, comparison and appearance controls. No inference imports at startup."""
import json
import os
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QStandardPaths
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QListWidget, QListWidgetItem, QFileDialog, QComboBox, QAbstractButton
from PySide6.QtGui import QIcon
from .widgets import ComboBox
from .i18n import tr, set_language
from . import DISPLAY_VERSION


class Features:
    def build_features(self, results_layout, settings_layout):
        from .ui import Preview, label
        self.similarity = None
        self.ranking_results = {}
        self.comparison_results = []
        self.query_face = None

        page = QWidget(); layout = QVBoxLayout(page)
        self.rank_button = QPushButton('更新排行'); self.rank_button.clicked.connect(self.start_ranking)
        layout.addWidget(self.rank_button)
        grid = QGridLayout(); self.rank_cards = {}; self.rank_previews = {}; self.rank_labels = {}
        for row, group in enumerate(('male', 'female')):
            for col, kind in enumerate(('near', 'far')):
                card = QFrame(); card.setObjectName('card'); box = QVBoxLayout(card)
                title = ('男性' if group == 'male' else '女性') + (' · 最接近平均脸' if kind == 'near' else ' · 最不接近平均脸')
                box.addWidget(label(title, 'section'))
                preview = Preview(); preview.setMinimumSize(130,140); box.addWidget(preview,1)
                info = label('请先生成平均脸', 'muted'); info.setWordWrap(True); box.addWidget(info)
                key = group,kind
                self.rank_cards[key]=card; self.rank_previews[key]=preview; self.rank_labels[key]=info
                grid.addWidget(card,row,col)
        layout.addLayout(grid,1)
        layout.addWidget(label('相似度 · SFace 余弦相似度，范围 −1 至 1', 'muted'))
        self.tabs.insertTab(3,page,'排行')

        page = QWidget(); layout = QVBoxLayout(page)
        self.compare_button = QPushButton('上传照片并比对…'); self.compare_button.clicked.connect(self.choose_query)
        layout.addWidget(self.compare_button)
        content = QHBoxLayout(); left = QVBoxLayout()
        self.query_preview = Preview(); self.query_preview.setMinimumSize(160,200); self.query_preview.setMaximumWidth(240)
        self.query_name = label('选择一张单人照', 'muted'); self.query_name.setWordWrap(True)
        left.addWidget(self.query_preview); left.addWidget(self.query_name); left.addStretch(); content.addLayout(left)
        self.matches = QListWidget(); self.matches.setIconSize(QSize(75,100))
        self.matches.itemDoubleClicked.connect(self.inspect_match)
        content.addWidget(self.matches,1); layout.addLayout(content,1)
        layout.addWidget(label('前 10 个样本 · 相似度 · 分数越高越相似', 'muted'))
        self.tabs.insertTab(4,page,'比对')
        settings_layout.insertWidget(0,label('外观', 'section'))
        self.theme_choice = ComboBox()
        self.theme_choice.addItem('浅色模式', 'light')
        self.theme_choice.addItem('深色模式', 'dark')
        settings_layout.insertWidget(1,self.theme_choice)
        settings_layout.insertWidget(2,label('语言/Language', 'section'))
        self.language_choice = ComboBox()
        for name, code in [('中文','zh'),('English','en'),('日本語','ja')]: self.language_choice.addItem(name,code)
        settings_layout.insertWidget(3,self.language_choice)
        self.language_choice.currentIndexChanged.connect(self.apply_language)
        self.theme_choice.currentIndexChanged.connect(self.apply_theme)
        self.tabs.currentChanged.connect(self.feature_tab_changed)
        self.actions.extend([self.rank_button,self.compare_button])

    def feature_tab_changed(self, index):
        if index == 3 and self.results and not self.ranking_results and not self.busy:
            self.start_ranking()

    def get_similarity(self):
        if self.similarity is None:
            from .similarity import Similarity
            self.similarity = Similarity()
        return self.similarity

    def start_ranking(self):
        if self.busy or not self.results: return
        from .ui import Worker
        self.worker = Worker('rank', similarity=self.get_similarity(), faces=list(self.faces), averages=dict(self.results))
        self.worker.result.connect(self.show_ranking); self.start_worker()

    def show_ranking(self, result):
        self.ranking_results = result
        for group in ('male','female'):
            for i, kind in enumerate(('near','far')):
                key = group,kind
                self.rank_cards[key].setVisible(group in self.results)
                if group in result:
                    face,score = result[group][i]
                    self.rank_previews[key].show_image(face.image)
                    self.rank_labels[key].setText(self.face_name(face) + '\n' + tr('相似度：{score}').format(score=f'{score:.4f}'))

    def choose_query(self):
        if self.busy or not any(f.enabled for f in self.faces):return
        path,_ = QFileDialog.getOpenFileName(self,tr('选择一张单人照'),'',tr('图片 (*.png *.jpg *.jpeg)'))
        if path:self.start_compare(path)

    def start_compare(self, path):
        if self.busy:return
        from .ui import Worker
        self.comparison_results=[]; self.query_face=None; self.matches.clear(); self.query_preview.show_image(None)
        self.query_name.setText(Path(path).name)
        options={'backend':self.backend_choice.currentData()}
        if options['backend']=='insightface':options['model_dir']=self.research_dir
        self.worker=Worker('compare',similarity=self.get_similarity(),faces=list(self.faces),path=path,engine_options=options)
        self.worker.result.connect(self.show_comparison); self.start_worker()

    def show_comparison(self, payload):
        from .ui import pixmap
        self.query_face,self.comparison_results=payload
        self.query_preview.show_image(self.query_face.image)
        self.matches.clear()
        for rank,(face,score) in enumerate(self.comparison_results,1):
            text=f'{rank:02d}   {self.face_name(face)}\n'+tr('相似度：{score}').format(score=f'{score:.4f}')
            item=QListWidgetItem(QIcon(pixmap(face.image).scaled(75,100,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)),text)
            item.setData(Qt.ItemDataRole.UserRole,face.id); self.matches.addItem(item)

    def inspect_match(self,item):
        face_id=item.data(Qt.ItemDataRole.UserRole)
        for i,face in enumerate(self.faces):
            if face.id==face_id:
                proxy=QListWidgetItem(); proxy.setData(Qt.ItemDataRole.UserRole,i); self.inspect_face(proxy); break

    def face_name(self,face):
        return Path(face.source).name+(tr(' · 人脸 {index}').format(index=face.index) if face.group_photo else '')

    def invalidate_features(self):
        self.ranking_results={}; self.comparison_results=[]; self.query_face=None
        if hasattr(self,'matches'):
            self.matches.clear(); self.query_preview.show_image(None); self.query_name.setText(tr('选择一张单人照'))
            for key,preview in self.rank_previews.items():
                preview.show_image(None); self.rank_labels[key].setText(tr('请先生成平均脸'))

    def capture_translations(self):
        # Capture source strings once, before applying the persisted language.
        dynamic={self.counts,self.status,self.checked_label,self.query_name,*self.result_labels.values(),*self.rank_labels.values(),*self.previews.values(),*self.rank_previews.values(),self.query_preview}
        self.text_bindings=[]; self.tooltip_bindings=[]; self.combo_bindings=[]
        for obj in self.findChildren(QWidget):
            if isinstance(obj,(QLabel,QAbstractButton)) and obj not in dynamic:
                self.text_bindings.append((obj,obj.text()))
            if obj.toolTip():self.tooltip_bindings.append((obj,obj.toolTip()))
            if isinstance(obj,QComboBox) and obj is not self.language_choice:
                for i in range(obj.count()):self.combo_bindings.append((obj,i,obj.itemText(i)))
        self.tab_sources=[self.tabs.tabText(i) for i in range(self.tabs.count())]
        self.menu_bindings=[(action,action.text()) for button in self.actions[:4] for action in button.menu().actions()]

    def apply_language(self, *args):
        code=self.language_choice.currentData(); set_language(code)
        for obj,source in self.text_bindings:obj.setText(tr(source))
        for obj,source in self.tooltip_bindings:obj.setToolTip(tr(source))
        for obj,source in self.menu_bindings:obj.setText(tr(source))
        for obj,i,source in self.combo_bindings:obj.setItemText(i,tr(source))
        for i,source in enumerate(self.tab_sources):self.tabs.setTabText(i,tr(source))
        title=tr('平均脸生成器')+' · Average Face Generator' if code!='en' else 'Average Face Generator'
        self.setWindowTitle(f'{title} {DISPLAY_VERSION}')
        self.table.setHorizontalHeaderLabels([tr('参数'),tr('男性组'),tr('女性组')])
        self.logs.setPlaceholderText(tr('暂无处理记录'))
        if self.research_dir:self.model_folder_button.setText(tr('模型包：{0}').format(Path(self.research_dir).name))
        self.rebuild_list(); self.update_counts(); self.show_results(self.results)
        if self.ranking_results:self.show_ranking(self.ranking_results)
        else:
            for info in self.rank_labels.values():info.setText(tr('请先生成平均脸'))
        if self.query_face:self.show_comparison((self.query_face,self.comparison_results))
        else:self.query_name.setText(tr('选择一张单人照'))
        for preview in [*self.previews.values(),*self.rank_previews.values(),self.query_preview]:preview.redraw()
        if not self.busy:self.status.setText(tr('就绪'))
        self.save_preferences()

    def apply_theme(self, *args):
        from .ui import STYLE
        from .common import resource_dir
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPalette, QColor
        dark=self.theme_choice.currentData()=='dark'
        style=STYLE.replace('@ASSETS@',(resource_dir()/'assets').as_posix())
        if dark:
            colors={'#f3f5f9':'#121821','white':'#1c2532','#202a3a':'#e6edf7','#e1e6ee':'#344154','#536174':'#b1bfd1','#dce2ec':'#3c4a5f','#f1f4ff':'#27354d','#a0a8b5':'#79869a','#f2f4f7':'#202938','#e5e8ed':'#334052','#aebbe9':'#384975','#e9eeff':'#2c3e60','#304aa3':'#bdceff','#f5f7fc':'#202b3c','#e5e9f2':'#263246','#edf1ff':'#2a3a56','#c3cbd9':'#52627b','#92a1b8':'#7a8fae','#f8faff':'#202a39','#eef1f7':'#2e3a4d','#aeb9ca':'#6c7d96','#f1f4f9':'#151e2c','#4968e8':'#7892ff'}
            import re
            style=re.sub('|'.join(re.escape(x) for x in colors),lambda m:colors[m.group()],style)
            style+=' QPushButton#primary, QListWidget::indicator:checked {color: #ffffff;} QToolTip {background:#e6edf7;color:#121821;}'
        app=QApplication.instance()
        app.setProperty('avgfaceDarkTheme',dark)
        app.setStyleSheet(style)
        palette=app.style().standardPalette()
        if dark:
            for role,color in [(QPalette.ColorRole.Window,'#121821'),(QPalette.ColorRole.Base,'#1c2532'),(QPalette.ColorRole.Text,'#e6edf7'),(QPalette.ColorRole.WindowText,'#e6edf7'),(QPalette.ColorRole.Button,'#1c2532'),(QPalette.ColorRole.ButtonText,'#e6edf7'),(QPalette.ColorRole.Highlight,'#2a3a56'),(QPalette.ColorRole.HighlightedText,'#e6edf7')]:palette.setColor(role,QColor(color))
        app.setPalette(palette); self.save_preferences()

    def preferences_path(self):
        override=os.environ.get('AVGFACE_SETTINGS_PATH')
        if override:return Path(override)
        if os.environ.get('QT_QPA_PLATFORM')=='offscreen':return None
        return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'AverageFaceGenerator'/'preferences.json'

    def save_preferences(self):
        if not getattr(self,'preferences_ready',False):return
        path=self.preferences_path()
        if path:
            try:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps({'language':self.language_choice.currentData(),'dark':self.theme_choice.currentData()=='dark','auto_gender':self.auto_gender_check.isChecked()}),encoding='utf-8')
            except OSError:pass

    def load_preferences(self):
        path=self.preferences_path(); prefs={}
        if path:
            try:prefs=json.loads(path.read_text('utf-8'))
            except (OSError,ValueError):pass
        if not isinstance(prefs,dict):prefs={}
        self.language_choice.setCurrentIndex(max(0,self.language_choice.findData(prefs.get('language','zh'))))
        self.theme_choice.setCurrentIndex(1 if prefs.get('dark') is True else 0)
        self.auto_gender_check.setChecked(prefs.get('auto_gender',True) is not False)
        self.apply_language(); self.apply_theme(); self.preferences_ready=True
