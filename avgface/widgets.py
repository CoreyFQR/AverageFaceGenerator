"""Rounded popups without the native square combo container."""
from PySide6.QtCore import Qt, QPoint, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QRegion, QColor, QPen
from PySide6.QtWidgets import QApplication, QComboBox, QMenu


class RoundedMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

    def showEvent(self, event):
        anchor = self.parentWidget()
        if anchor:
            self.setFixedWidth(anchor.width())
        super().showEvent(event)
        path=QPainterPath()
        path.addRoundedRect(QRectF(self.rect()),10,10)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def paintEvent(self, event):
        # Use a normal opaque Windows popup, avoiding layered-window composition.
        # Draw the border AFTER Qt paints the solid panel and menu items. Inset
        # the stroke from the native region so its antialiasing is not clipped.
        super().paintEvent(event)
        # A Windows/system palette can stay dark while the application QSS is
        # light. Use the explicitly selected theme, including for existing menus.
        dark = bool(QApplication.instance().property('avgfaceDarkTheme'))
        border = QColor('#344154' if dark else '#e1e6ee')
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(border, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(1.5,1.5,-1.5,-1.5),9,9)
        painter.end()


class ComboBox(QComboBox):
    def showPopup(self):
        if hasattr(self, 'popup_menu'):
            self.popup_menu.close()
            self.popup_menu.deleteLater()
        menu = RoundedMenu(self)
        for i in range(self.count()):
            action = menu.addAction(self.itemText(i))
            action.setEnabled(bool(self.model().item(i).isEnabled()))
            action.triggered.connect(lambda checked=False, index=i: self.setCurrentIndex(index))
            if i == self.currentIndex():
                menu.setActiveAction(action)
        menu.setFixedWidth(self.width())
        self.popup_menu = menu
        menu.popup(self.mapToGlobal(QPoint(0, self.height() + 4)))

    def hidePopup(self):
        if hasattr(self, 'popup_menu'):
            self.popup_menu.close()
        super().hidePopup()
