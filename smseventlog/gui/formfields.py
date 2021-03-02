import inspect

from .__init__ import *
from .. import functions as f
from distutils.util import strtobool

# map obj: (getter, setter)
global obj_vals
obj_vals = {
    QComboBox: ('currentText', 'setCurrentText', 'currentIndexChanged'),
    QTextEdit: ('toPlainText', 'setText', 'textChanged'),
    QLineEdit: ('text', 'setText', 'textChanged'),
    QDateEdit: ('dateTime.toPyDateTime', 'setDate', 'dateChanged'),
    QCheckBox: ('isChecked', 'setChecked', 'stateChanged'),
    QSpinBox: ('value', 'setValue', 'valueChanged'),
    QSlider: ('value', 'setValue', 'valueChanged'),
    QRadioButton: ('isChecked', 'setChecked', 'toggled')}

class FormFields(object):
    # simplify getting/setting all form field values
    changed = pyqtSignal(object) # connect all "changed" signals to common signal

    def __init__(self, name=None, *args, **kw):
        super().__init__(*args, **kw)

        # loop base classes till find a match in obj_vals
        for cls in inspect.getmro(self.__class__):
            type_ = obj_vals.get(cls, None)
            if not type_ is None:
                parentclass = cls # eg PyQt5.QtWidgets.QTextEdit, (class object not str)
                break

        getter, setter = type_[0], type_[1] # currentText, setCurrentText
        f.set_self(vars())

        # changed signal
        getattr(self, type_[2]).connect(lambda x: self.changed.emit(x))

        if not name is None:
            self.set_name(name=name)

    @property
    def val(self):
        v = f.getattr_chained(self, self.getter) # chained because DateEdit needs multi method() calls
        if isinstance(v, str):
            return v.strip()
        else:
            return v

    @val.setter
    def val(self, value):
        self._set_val(value)

    def _set_val(self, value):
        getattr(self, self.setter)(value)

    def set_name(self, name):
        # give widget a unique objectName to save/restore state
        self.name = name
        if hasattr(self, 'setObjectName'):
            self.setObjectName(f'{name}_{self.parentclass.__name__}'.replace(' ', '').lower())
    
    def select_all(self):
        try:
            self.setFocus()
            self.selectAll()
        except:
            print(f'{self.__class__.__name__}: couldnt select all text')
            pass # NOTE not sure which methods select text in all types of boxes yet

class ComboBox(QComboBox, FormFields):
    def __init__(self, items=None, editable=True, default=None, *args, **kw):
        super().__init__(*args, **kw)
        self.setMaxVisibleItems(20)
        self.setEditable(editable)
        self.setDuplicatesEnabled(False)
        self.set_items(items)

        if default:
            self.val = default
    
    @FormFields.val.setter
    def val(self, value):
        # prevent adding previous default items not in this list, allow wildcards
        val_lower = str(value).lower()

        if '*' in value:
            self._set_val(value) # just use setText

        elif val_lower in self.items_lower:
            idx = self.items_lower.index(val_lower)
            self.setCurrentIndex(idx)
    
    def select_all(self):
        self.setFocus()
        self.lineEdit().selectAll()
    
    def set_items(self, items):
        """Clear all items and add new"""
        if items is None:
            items = []

        self.items = items
        self.items_original = items
        self.items_lower = [str(item).lower() for item in self.items]

        self.clear()
        self.addItems(items)
    
    def reset(self):
        self.set_items(items=self.items_original)

class ComboBoxTable(ComboBox):
    """
    Special combo box for use as cell editor in TableView

    To implement a persistent state for the widgetd cell, must provide
    `getWidgetedCellState` and `setWidgetedCellState` methods.  This is how
    the WidgetedCell framework can create and destory widget as needed.
    """
    escapePressed = pyqtSignal()
    returnPressed = pyqtSignal()

    def __init__(self, parent=None, delegate=None, **kw):
        super().__init__(parent=parent, **kw)
        # need parent so TableView knows where to draw editor
        
        self.delegate = delegate
        if not delegate is None:
            self.escapePressed.connect(self.delegate.close_editor)
            # self.returnPressed.connect(self.delegate.commitAndCloseEditor)

    # NOTE not sure if this is still needed 2020-08-21
    # def keyPressEvent(self, event):
    #     if event.key() in (Qt.Key_Return, Qt.Key_Enter):
    #         print('returnPressed')
    #         # self.delegate.commitAndCloseEditor()
    #         self.returnPressed.emit()
    #         return

    #     return super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.escapePressed.emit()
        return super().eventFilter(obj, event)
    
    def commit_list_data(self):
        # need to manually set the editors's index/value when list item is pressed, then commit
        self.setCurrentIndex(self.view().currentIndex().row())
        self.delegate.commitAndCloseEditor()

    def showPopup(self):
        # need event filter to catch combobox view's ESC event and close editor completely
        super().showPopup()
        view = self.view()
        view.installEventFilter(self)
        view.pressed.connect(self.commit_list_data)

    def getWidgetedCellState(self):
        return self.currentIndex()

    def setWidgetedCellState(self, state):
        self.setCurrentIndex(state)


class TextEdit(QTextEdit, FormFields):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.setTabChangesFocus(True)

class LineEdit(QLineEdit, FormFields):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

class DateEdit(QDateEdit, FormFields):
    def __init__(self, date=None, calendar=True, *args, **kw):
        super().__init__(*args, **kw)
        editor_format = 'yyyy-MM-dd'
        display_format = '%Y-%m-%d' # not sure if used
        self.setCalendarPopup(calendar)
        self.setDisplayFormat(editor_format)

        if date is None:
            date = dt.now().date()
        
        self.setDate(date)

class CheckBox(QCheckBox, FormFields):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        # self.setChecked(checked) # maybe dont need this
        # self.setEnabled(enabled)
    
    @FormFields.val.setter
    def val(self, value):
        # windows saves bools as 'true'/'false'
        if not value in (True, False):
            try:
                value = strtobool(value)
            except:
                value = False
        self._set_val(value)

class SpinBox(QSpinBox, FormFields):
    def __init__(self, range=None, *args, **kw):
        super().__init__(*args, **kw)
        if not range is None:
            self.setRange(*range)

    @FormFields.val.getter
    def val(self):
        # Always return None instead of 0
        # NOTE this may need to change but is good for now
        v = super().val
        return v if not v == 0 else None
