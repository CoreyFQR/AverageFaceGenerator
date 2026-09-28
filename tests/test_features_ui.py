import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import json
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from avgface.ui import Window,configure_app
from test_engine import fixture_face


@pytest.fixture
def app():
    app=QApplication.instance() or QApplication([]); configure_app(app); return app


def test_language_theme_preferences_preserve_samples_and_results(app,tmp_path,monkeypatch):
    monkeypatch.setenv('AVGFACE_SETTINGS_PATH',str(tmp_path/'preferences.json'))
    window=Window(); face=fixture_face(); window.add_faces([face]); window.show_results({'male':(face.image,face.points)})
    assert [window.tabs.tabText(i) for i in range(7)]==['平均脸','样本','统计','排行','比对','记录','设置']
    window.language_choice.setCurrentIndex(1); window.theme_choice.setCurrentIndex(1)
    assert window.generate.text()=='Generate average'
    assert window.actions[0].menu().actions()[0].text()=='Choose photos…'
    assert window.tabs.tabText(3)=='Ranking' and window.faces==[face] and 'male' in window.results
    assert '#121821' in app.styleSheet()
    window.language_choice.setCurrentIndex(2)
    assert window.tabs.tabText(6)=='設定'
    assert json.loads((tmp_path/'preferences.json').read_text())=={'language':'ja','dark':True,'auto_gender':True}
    window.close()
    restored=Window(); assert restored.language_choice.currentData()=='ja' and restored.theme_choice.currentData()=='dark'
    assert restored.auto_gender_check.isChecked() is True
    restored.close()


def test_popup_has_anchor_width_and_opaque_windows_surface(app):
    window=Window(); window.show(); window.tabs.setCurrentIndex(6); app.processEvents()
    combo=window.backend_choice; combo.showPopup(); app.processEvents()
    assert combo.popup_menu.width()==combo.width()
    assert not combo.popup_menu.mask().isEmpty()
    assert not combo.popup_menu.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    image=combo.popup_menu.grab().toImage()
    assert image.pixelColor(image.width()//2,image.height()//2).alpha()==255
    assert image.pixelColor(image.width()//2,image.height()//2).lightness()>200
    combo.popup_menu.actions()[1].trigger(); assert combo.currentData()=='insightface'
    combo.hidePopup(); window.close()


def test_changes_clear_rankings_and_comparisons(app):
    window=Window(); face=fixture_face(); window.add_faces([face]); window.rebuild_list()
    window.show_results({'male':(face.image,face.points)})
    window.show_ranking({'male':((face,1.),(face,1.))})
    window.show_comparison((face,[(face,1.)]))
    window.list.item(0).setSelected(True); window.change_selected('female')
    assert not window.results and not window.ranking_results and not window.comparison_results
    assert window.matches.count()==0 and window.query_face is None
    window.close()


@pytest.mark.parametrize('enabled', [False, True])
def test_auto_gender_toggle_persists_without_other_setting_changes(app,tmp_path,monkeypatch,enabled):
    from avgface import i18n
    monkeypatch.setattr(i18n,'LANGUAGE',i18n.LANGUAGE)
    path=tmp_path/'preferences.json'
    path.write_text(json.dumps({'language':'en','dark':True,'auto_gender':not enabled}))
    monkeypatch.setenv('AVGFACE_SETTINGS_PATH',str(path))
    window=Window()
    assert window.auto_gender_check.isChecked() is not enabled
    window.auto_gender_check.click()
    assert json.loads(path.read_text())=={'language':'en','dark':True,'auto_gender':enabled}
    window.close()
    restored=Window()
    assert restored.auto_gender_check.isChecked() is enabled
    restored.close()
