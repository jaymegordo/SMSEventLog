from . import gui as ui
from .formfields import ComboBoxTable
from .datamodel import TableModel
from .__init__ import *

log = logging.getLogger(__name__)
global m_align
m_align =  {
    'object': Qt.AlignLeft,
    'float64': Qt.AlignRight,
    'int64': Qt.AlignRight,
    'bool': Qt.AlignCenter,
    'datetime64[ns]': Qt.AlignCenter}

# TODO maybe move to formfields
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
            self.returnPressed.emit()
            return

        super().keyPressEvent(event)

class CellDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.index = None
    
    def _initStyleOption(self, option, index):
        # bypass to parent
        super().initStyleOption(option, index)
    
    def initStyleOption(self, option, index):
        # set column alignment based on data type
        model = self.parent.model()
        icol = index.column()
        dtype = model.get_dtype(icol=icol)
        
        # align all cols except 'longtext' VCenter
        alignment = m_align.get(dtype, Qt.AlignLeft)
        col_name = model.get_col_name(icol=icol)

        if not col_name in self.parent.mcols['longtext']:
            alignment |= Qt.AlignVCenter

        option.displayAlignment = alignment
        self._initStyleOption(option, index)
    
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width() + 2, size.height() + 2)

    def paint_(self, qPainter, option, qModelIndex):
        # not used, for example only rn
        v4Option = QStyleOptionViewItem(option)
        v4Option.index = qModelIndex
        value = qModelIndex.data()
        v4Option.text = str(value)

        parent = self.parent
        style = parent.style()

        if (v4Option.state & QStyle.State_HasFocus):
            # --- The table cell with focus
            # Draw the background
            style.drawPrimitive(style.PE_PanelItemViewItem, v4Option, qPainter, parent)

            # Draw the text
            subRect = style.subElementRect(style.SE_ItemViewItemText, v4Option, parent)
            alignment = qModelIndex.data(Qt.TextAlignmentRole)
            if not alignment:
                alignment = int(Qt.AlignLeft | Qt.AlignVCenter)
            if (v4Option.state & QStyle.State_Enabled):
                itemEnabled = True
            else:
                itemEnabled = False
            textRect = style.itemTextRect(v4Option.fontMetrics, subRect, alignment, itemEnabled, value)
            style.drawItemText(qPainter, textRect, alignment, v4Option.palette, v4Option.state, value)

            # Draw the focus rectangle
            focusOption = QStyleOptionFocusRect()
            focusOption.rect = v4Option.rect
            style.drawPrimitive(style.PE_FrameFocusRect, focusOption, qPainter, parent)
        else:
            # --- All other table cells
            style.drawControl(style.CE_ItemViewItem, v4Option, qPainter, parent)

    def createEditor(self, parent, option, index):
        self.index = index
        editor = TextEditor(parent=parent)

        # TODO: only do this if cell height is smaller than...?
        editor.setMinimumHeight(self.parent.rowHeight(index.row()) + 10)
        editor.returnPressed.connect(self.commitAndCloseEditor)
        self.editor = editor
        return editor          

    def setEditorData(self, editor, index):
        val = index.data(role=Qt.EditRole)

        if isinstance(editor, QTextEdit):
            editor.setText(str(val))

            # move cursor to end for long items, else highlight everything for quicker editing
            if len(str(val)) > 20:
                editor.moveCursor(QTextCursor.End)
            else:
                editor.selectAll()

    def setModelData(self, editor, model, index):
        model.setData(index=index, val=editor.toPlainText(), role=Qt.EditRole)

    def close_editor(self):
        self.closeEditor.emit(self.editor, QStyledItemDelegate.NoHint)

    def commitAndCloseEditor(self):
        editor = self.editor
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)
        self.parent.resizeRowToContents(self.index.row())


class ComboDelegate(CellDelegate):
    def __init__(self, parent, items):
        super().__init__(parent)
        # parent is TableView

        items_lower = [item.lower() for item in items]
        _cell_widget_states = {}
        f.set_self(vars())

    def initStyleOption(self, option, index):
        option.displayAlignment = Qt.AlignCenter
        self._initStyleOption(option, index)

    def createEditor(self, parent, option, index):
        self.index = index
        editor = ComboBoxTable(parent=parent, delegate=self, items=self.items)
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
            if val in self.items:
                num = self.items.index(val)
                editor.setCurrentIndex(num)
            editor.lineEdit().selectAll()

        except:
            f.send_error()

    def setModelData(self, editor, model, index):
        # convert any matching string to good value even if case mismatched
        val = editor.val
        val_lower = val.lower()

        if val_lower in self.items_lower:
            val = self.items[self.items_lower.index(val_lower)]
            model.setData(index=index, val=val, role=Qt.EditRole)
        else:
            msg = f'Error setting value: "{val}" not in list.'
            self.parent.update_statusbar(msg=msg)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class DateDelegateBase(CellDelegate):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

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
        val = index.data(role=TableModel.RawDataRole)

        if pd.isnull(val):
            val = self.cur_date

        getattr(editor, self.set_editor)(val)

    def setModelData(self, editor, model, index):
        editor_date = getattr(editor, self.date_type)()
        d = QDateTime(editor_date).toPyDateTime()
        model.setData(index, d)

# TODO use formfields.DateEdit/DateTimeEdit
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
        f.set_self(vars())
    
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
        f.set_self(vars())        
