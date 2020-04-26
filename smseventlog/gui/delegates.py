from .__init__ import *
from . import (
    gui as ui)

log = logging.getLogger(__name__)

# TODO: Int columns

class TextEditor(QTextEdit):
    returnPressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTabChangesFocus(True)
        # self.textChanged.connect(self.textHasChanged) # need to make this func

    def keyPressEvent(self, event):       
        modifiers = QApplication.keyboardModifiers()
        
        if (modifiers != Qt.ShiftModifier and 
            event.key() in (Qt.Key_Return, Qt.Key_Enter)):
            # print(event.key())
            self.returnPressed.emit()
            return

        super(TextEditor, self).keyPressEvent(event)

class AlignDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super(AlignDelegate, self).initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter

class EditorDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        QStyledItemDelegate.__init__(self, parent=parent)
        self.parent = parent
        self.index = None
    
    def createEditor(self, parent, option, index):
        self.index = index
        editor = TextEditor(parent=parent)

        # TODO: only do this if cell height is smaller than...?
        editor.setMinimumHeight(self.parent.rowHeight(index.row()) + 10)
        editor.returnPressed.connect(self.commitAndCloseEditor)
        self.editor = editor
        return editor          

    def setEditorData(self, editor, index):
        val = index.model().data(index)

        if isinstance(editor, QTextEdit):
            editor.setText(val)
            editor.moveCursor(QTextCursor.End)

    def setModelData(self, editor, model, index):
        # TODO: Check if text has changed, don't commit
        model.setData(index=index, val=editor.toPlainText(), role=Qt.EditRole)

    def commitAndCloseEditor(self):
        # editor = self.sender()
        editor = self.editor
        self.commitData.emit(editor)
        self.parent.resizeRowToContents(self.index.row())
        self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)

class DateColumnDelegate(EditorDelegate):
    def __init__(self, parent=None):
        super(DateColumnDelegate, self).__init__(parent=parent)
        self.format = 'yyyy-MM-dd'

    def initStyleOption(self, option, index):
        super(DateColumnDelegate, self).initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter

    def old_sizeHint(self, option, index):
        return
        size = super(DateColumnDelegate, self).sizeHint(option, index)
        size.setWidth(40)
        return size

    def displayText(self, value, locale):
        dtformat = '%Y-%m-%d'
        if isinstance(value, dt) and not pd.isnull(value):
            return value.strftime(dtformat)
        else:
            return ''

    def createEditor(self, parent, option, index):
        self.index = index
        editor = QDateEdit(parent)
        editor.setDisplayFormat(self.format)
        editor.setCalendarPopup(True)
        editor.setMinimumWidth(self.parent.columnWidth(index.column()) + 10) # add 10px (editor cuts off date)

        calendar = editor.calendarWidget()
        calendar.clicked.connect(self.commitAndCloseEditor)
        self.editor = editor

        return editor

    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.EditRole)

        if pd.isnull(val):
            # val = QDateTime.currentDateTime().toPyDateTime()
            val = dt.now().date()

        editor.setDate(val)

    def setModelData(self, editor, model, index):
        d = QDateTime(editor.date()).toPyDateTime()
        model.setData(index, d)

        
