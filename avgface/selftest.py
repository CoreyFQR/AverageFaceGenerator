"""Run packaged offline smoke test without opening the interactive window."""
import json
import os
import sys
import traceback
from pathlib import Path


def native_menus(window, output):
    """Check pixels read from actual, non-layered Windows popup surfaces."""
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import QApplication
    def settle():
        loop=QEventLoop(); QTimer.singleShot(100,loop.quit); loop.exec()
    window.tabs.setCurrentIndex(6)
    captures=0
    for step,dark in enumerate((False,True,False)):
        window.theme_choice.setCurrentIndex(int(dark))
        # Reproduce a native/system palette that disagrees with the app theme.
        # Border painting must use the selected theme, including after toggles.
        palette=QApplication.palette()
        palette.setColor(QPalette.ColorRole.Base,QColor('white' if dark else '#121821'))
        QApplication.setPalette(palette)
        for name in ('import','filter','theme','language','model'):
            combo={'filter':window.filter,'theme':window.theme_choice,'language':window.language_choice,'model':window.backend_choice}.get(name)
            window.tabs.setCurrentIndex(1 if name=='filter' else 6)
            QApplication.processEvents()
            if combo:
                combo.showPopup(); menu=combo.popup_menu; anchor=combo
            else:
                anchor=window.actions[3]; menu=anchor.menu()
                menu.popup(anchor.mapToGlobal(anchor.rect().bottomLeft()))
            menu.setActiveAction(None); settle()
            shot=menu.screen().grabWindow(int(menu.winId()))
            assert not shot.isNull() and menu.width()==anchor.width()
            shot.save(str(output.with_name(f'{output.stem}-{name}-{step}.png')))
            image=shot.toImage()
            pixel=image.pixelColor(image.width()//2,image.height()-round(5*shot.devicePixelRatio()))
            expected=(28,37,50) if dark else (255,255,255)
            assert pixel.getRgb()[:3]==expected,(name,dark,pixel.getRgb())
            border='#344154' if dark else '#e1e6ee'
            # Check the actual visible stroke on all four straight edges.
            span=range(round(4*shot.devicePixelRatio()))
            edges=[[(image.width()//2,y) for y in span],
                   [(image.width()//2,image.height()-1-y) for y in span],
                   [(x,image.height()//2) for x in span],
                   [(image.width()-1-x,image.height()//2) for x in span]]
            for edge in edges:
                colors=[image.pixelColor(x,y).name() for x,y in edge]
                assert border in colors,(name,dark,border,colors)
            menu.close(); captures+=1
    return captures


def main():
    output=Path(sys.argv[sys.argv.index("--self-test")+1])
    try:
        native='--native-menus' in sys.argv
        os.environ["QT_QPA_PLATFORM"]='windows' if native else 'offscreen'
        os.environ['AVGFACE_SETTINGS_PATH']=str(output.with_suffix('.preferences.json'))
        from PySide6.QtWidgets import QApplication
        from .ui import Window, configure_app
        from .engine import Engine, average, write_image
        import numpy as np
        app=QApplication([]); configure_app(app)
        window=Window(); window.show(); app.processEvents()
        from . import DISPLAY_VERSION
        assert app.applicationVersion()==DISPLAY_VERSION and DISPLAY_VERSION in window.windowTitle()
        assert not app.windowIcon().isNull() and not window.windowIcon().isNull()
        window.auto_gender_check.setChecked(True)
        window.auto_gender_check.setChecked(False)
        restored=Window()
        assert not restored.auto_gender_check.isChecked()
        restored.close()
        window.auto_gender_check.setChecked(True)
        backend=sys.argv[sys.argv.index('--backend')+1] if '--backend' in sys.argv else 'open'
        model_dir=sys.argv[sys.argv.index('--model-dir')+1] if '--model-dir' in sys.argv else None
        engine=Engine(model_dir=model_dir,backend=backend)
        report={"model_load":True,"empty_detection":len(engine.detect(np.zeros((640,640,3),np.uint8)))==0,"ui":True,
                "application_icon":True,"auto_gender_preference":True,"version":app.applicationVersion()}
        if "--photo" in sys.argv:
            photo=sys.argv[sys.argv.index("--photo")+1]
            if '--group-photo' in sys.argv:
                from .importer import ImportSession
                from .common import resource_dir
                import hashlib
                session=ImportSession()
                try:
                    rows=list(session.iterate([photo,photo],'auto',True,lambda:False,
                                              {'auto_gender':True},set()))
                    faces=[face for _,(items,_) in rows for face in items]
                    notes=[note for _,(_,messages) in rows for note in messages]
                    assert len(faces)>1 and len({face.id for face in faces})==len(faces)
                    assert all(face.group in ('male','female') for face in faces)
                    report.update(auto_gender=True,batch_dedup=True,
                                  gender_counts={g:sum(f.group==g for f in faces) for g in ('male','female')},
                                  gender_model_sha256=hashlib.sha256((resource_dir()/'models'/'realistic_gender.onnx').read_bytes()).hexdigest())
                finally:session.close()
            else:
                faces,notes=engine.process(photo)
            report.update(faces=len(faces),notes=notes,backend=backend)
            if not faces:raise RuntimeError("Smoke-test photo produced no face")
            for face in faces:face.group="male"
            window.add_faces(faces); window.rebuild_list()
            img,points=average(faces)
            window.show_results({"male":(img,points)})
            from .similarity import Similarity
            similarity=Similarity()
            ranking=similarity.rank(faces,window.results)
            matches=similarity.compare(faces[0],faces)
            assert all(item[0].id in {face.id for face in faces} for item in ranking['male'])
            assert ranking['male'][0][1]>=ranking['male'][1][1]
            if len(faces)==1:assert ranking['male'][0][0].id==faces[0].id
            assert matches[0][0].id==faces[0].id and matches[0][1]>.999
            window.show_ranking(ranking); window.show_comparison((faces[0],matches))
            window.language_choice.setCurrentIndex(1); window.theme_choice.setCurrentIndex(1)
            assert window.tabs.tabText(3)=='Ranking'
            window.language_choice.setCurrentIndex(2); assert window.tabs.tabText(6)=='設定'
            window.language_choice.setCurrentIndex(0); window.theme_choice.setCurrentIndex(0)
            report.update(ranking=True,comparison=True,languages=['zh','en','ja'],dark_mode=True,self_match_score=matches[0][1])
            app.processEvents()
            write_image(output.with_suffix(".png"),img)
        window.grab().save(str(output.with_name(output.stem+"-ui.png")))
        if native:report['native_menu_captures']=native_menus(window,output)
        engine.close()
        output.write_text(json.dumps(report,indent=2),encoding="utf-8")
        return 0
    except Exception:
        output.write_text(traceback.format_exc(),encoding="utf-8")
        return 1
