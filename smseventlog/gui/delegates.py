from . import gui as ui
from .__init__ import *

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

        super().keyPressEvent(event)

class AlignDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        option.displayAlignment = Qt.AlignCenter
        super().initStyleOption(option, index)

class CellDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
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

    # def closeEditor(self, QWidget, hint=QAbstractItemDelegate.NoHint):
    #     return super().closeEditor(QWidget, hint=hint)

    def close_editor(self):
        print('close_editor')
        self.closeEditor.emit(self.editor, QStyledItemDelegate.NoHint)

    def commitAndCloseEditor(self):
        print('commit and closed editor')
        editor = self.editor
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)
        self.parent.resizeRowToContents(self.index.row())

    # def updateEditorGeometry(self, editor, option, index):
        # editor.setGeometry(option.rect)

class ComboWidget(QComboBox):
    """
    To implement a persistent state for the widgetd cell, you must provide
    a `getWidgetedCellState` and `setWidgetedCellState` methods.  This is how
    the WidgetedCell framework can create and destory your widget as needed.
    """
    escapePressed = pyqtSignal()
    returnPressed = pyqtSignal()

    def __init__(self, parent, delegate=None):
        super().__init__(parent)
        self.delegate = delegate
        self.setMaxVisibleItems(20)
        self.setEditable(True)
        self.setDuplicatesEnabled(False)
        self.escapePressed.connect(self.delegate.close_editor)

    def keyPressEvent(self, event):       
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.returnPressed.emit()
            return

        return super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.escapePressed.emit()
        return super().eventFilter(obj, event)
    
    def showPopup(self):
        # need event filter to catch combobox view's ESC event and close editor completely
        super().showPopup()
        view = self.view()
        view.installEventFilter(self)

    def getWidgetedCellState(self):
        return self.currentIndex()

    def setWidgetedCellState(self, state):
        self.setCurrentIndex(state)

class ComboDelegate(CellDelegate):
    def __init__(self, parent, items):
        super().__init__(parent)

        _cell_widget_states = {}
        f.set_self(self, vars())

    def createEditor(self, parent, option, index):
        self.index = index
        editor = ComboWidget(parent=parent, delegate=self)
        editor.addItems(self.items)
        editor.setMinimumWidth(editor.minimumSizeHint().width())

        self.editor = editor
        return editor

    def paint_(self, painter, option, index):
        # NOTE not used yet, maybe draw an arrow on the cell?
        val = index.data(Qt.DisplayRole)
        style = QApplication.instance().style()
        # style = ui.get_qt_app().style()

        opt = QStyleOptionComboBox()
        opt.text = str(val)
        opt.rect = option.rect
        style.drawComplexControl(QStyle.CC_ComboBox, opt, painter)
        super().paint(painter, option, index)

    def setEditorData(self, editor, index):
        val = index.data(Qt.DisplayRole)
        # print(val, type(val))
        try:
            num = self.items.index(val)
            editor.setCurrentIndex(num)
            editor.lineEdit().selectAll()
            # editor.showPopup()
            editor.currentIndexChanged.connect(self.commitAndCloseEditor)
        except:
            f.send_error()

    def setModelData(self, editor, model, index):
        model.setData(index=index, val=editor.currentText(), role=Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class DateDelegateBase(CellDelegate):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def initStyleOption(self, option, index):
        option.displayAlignment = Qt.AlignCenter
        super().initStyleOption(option, index)
    
    def paint(self, painter, option, index):
        # option.backgroundBrush = QBrush(Qt.red)
        option.backgroundBrush.setColor(QColor(100, 200, 100, 200))
        super().paint(painter, option, index)

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(self.width, size.height())

    def displayText(self, value, locale):
        # print(value, type(value))
        if isinstance(value, dt) and not pd.isnull(value):
            return value.strftime(self.display_format)
        else:
            return ''

    def createEditor(self, parent, option, index):
        self.index = index
        editor = self.date_editor(parent)
        editor.setDisplayFormat(self.editor_format)
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
            val = self.cur_date

        getattr(editor, self.set_editor)(val)

    def setModelData(self, editor, model, index):
        editor_date = getattr(editor, self.date_type)()
        d = QDateTime(editor_date).toPyDateTime()
        model.setData(index, d)

class DateTimeDelegate(DateDelegateBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        editor_format = 'yyyy-MM-dd hh:mm'
        display_format = '%Y-%m-%d     %H:%M'
        date_editor = QDateTimeEdit
        cur_date = dt.now()
        date_type = 'dateTime'
        set_editor = 'setDateTime'
        width = 144
        f.set_self(self, vars())
    
class DateDelegate(DateDelegateBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        editor_format = 'yyyy-MM-dd'
        display_format = '%Y-%m-%d'
        date_editor = QDateEdit
        cur_date = dt.now().date()
        date_type = 'date'
        set_editor = 'setDate'
        width = 90
        f.set_self(self, vars())        
