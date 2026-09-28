import os
os.environ["QT_QPA_PLATFORM"]="offscreen"
import pytest
from PySide6.QtWidgets import QApplication, QFileDialog
from avgface.ui import Window, configure_app
from test_engine import fixture_face


@pytest.fixture(scope="module")
def app():
    app=QApplication.instance() or QApplication([])
    configure_app(app)
    return app


def test_dedup_group_edits_invalidate_and_export(app,tmp_path,monkeypatch):
    window=Window()
    face=fixture_face()
    window.add_faces([face,face])
    assert len(window.faces)==1
    window.rebuild_list()
    window.show_results({"male":(face.image,face.points)})
    target=tmp_path/"平均脸.png"
    monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *a,**k:(str(target),"PNG"))
    window.export_image("male")
    assert target.is_file()
    window.list.item(0).setSelected(True)
    window.change_selected("female")
    assert face.group=="female"
    assert not window.results
    assert not window.export_buttons["male"].isEnabled()
    csv_path=tmp_path/"统计.csv"
    monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *a,**k:(str(csv_path),"CSV"))
    window.export_csv()
    assert "女性" in csv_path.read_text("utf-8-sig")
    window.close()


def test_review_only_cannot_generate(app):
    window=Window(); window.add_faces([fixture_face(group="review")])
    assert not window.generate.isEnabled()
    window.close()


@pytest.mark.parametrize('groups', [('male',), ('female',), ('male','female')])
def test_generate_only_populated_groups(app,groups):
    from avgface.ui import Worker
    window=Window()
    faces=[]
    for group in groups:
        face=fixture_face(group=group); face.id=group; faces.append(face)
    window.add_faces(faces)
    worker=Worker('average',faces=faces,normalize=True)
    errors=[]; worker.error.connect(errors.append); worker.result.connect(window.show_results); worker.run()
    assert not errors
    assert set(window.results)==set(groups)
    assert window.generate.text()=='生成平均脸'
    for group in ('male','female'):
        assert window.result_cards[group].isHidden()==(group not in groups)
        assert window.export_buttons[group].isEnabled()==(group in groups)
    assert not window.backend_choice.isEnabled()
    window.close()


def test_checkboxes_bulk_selection_survives_filter_and_updates_groups(app):
    from PySide6.QtCore import Qt
    window=Window()
    a,b,c=fixture_face(),fixture_face(group='female'),fixture_face(group='review')
    a.id,b.id,c.id='a','b','c'
    window.add_faces([a,b,c]); window.rebuild_list()
    window.list.item(0).setCheckState(Qt.CheckState.Checked)
    window.filter.setCurrentIndex(window.filter.findData('female'))
    window.check_visible('all')
    assert window.checked_ids=={'a','b'}
    window.change_selected('male')
    assert a.group==b.group=='male' and c.group=='review'
    window.filter.setCurrentIndex(0)
    window.check_visible('invert'); assert window.checked_ids=={'c'}
    window.change_selected(None); assert not c.enabled and a.enabled
    window.check_visible('none'); assert not window.checked_ids
    assert all(window.list.item(i).checkState()==Qt.CheckState.Unchecked for i in range(3))
    window.close()


def test_all_four_import_menus_preserve_mode_for_files_and_folders(app,monkeypatch):
    window=Window(); calls=[]
    monkeypatch.setattr(window,'choose_files',lambda mode,group:calls.append(('files',mode,group)))
    monkeypatch.setattr(window,'choose_folder',lambda mode,group:calls.append(('folder',mode,group)))
    for button,(mode,group) in zip(window.actions[:4],[('male',False),('female',False),('auto',False),('auto',True)]):
        for action in button.menu().actions():action.trigger()
        assert calls[-2:]==[('files',mode,group),('folder',mode,group)]
    window.close()


def test_single_photo_has_no_number_and_group_photo_keeps_face_index(app):
    window=Window(); a,b=fixture_face(),fixture_face(); b.id='two'; b.group_photo=True; b.index=7
    window.add_faces([a,b]); window.rebuild_list()
    assert '#1' not in window.list.item(0).text() and '人脸 1' not in window.list.item(0).text()
    assert '人脸 7' in window.list.item(1).text()
    window.close()


@pytest.mark.parametrize('dark_palette', [False, True])
def test_menu_borders_follow_selected_theme_despite_system_palette(app, dark_palette):
    from PySide6.QtGui import QColor, QPalette
    window = Window()
    window.show()
    original_palette = app.palette()
    try:
        # Import menus already exist, while combo popups are recreated each time.
        # Also exercise the dark -> light transition with a retained dark palette.
        for dark in (False, True, False):
            window.theme_choice.setCurrentIndex(int(dark))
            palette = app.palette()
            palette.setColor(QPalette.ColorRole.Base, QColor('#121821' if dark_palette else '#ffffff'))
            app.setPalette(palette)
            window.theme_choice.showPopup()
            for menu in (window.actions[3].menu(), window.theme_choice.popup_menu):
                menu.ensurePolished()
                menu.resize(menu.sizeHint())
                app.processEvents()
                shot = menu.grab()
                image = shot.toImage()
                x = image.width() // 2
                # At fractional DPI the one-pixel stroke is antialiased; at least
                # one fully covered pixel remains across the straight top edge.
                colors = [image.pixelColor(x, y).name() for y in range(round(4 * shot.devicePixelRatio()))]
                assert ('#344154' if dark else '#e1e6ee') in colors, (dark, dark_palette, colors)
            window.theme_choice.hidePopup()
    finally:
        window.close()
        app.setPalette(original_palette)
