from .__init__ import *
from .. import functions as f
from distutils.util import strtobool

# map obj: (getter, setter)
global obj_vals
obj_vals = {
    QComboBox: ('currentText', 'setCurrentText'),
    QTextEdit: ('toPlainText', 'setText'),
    QLineEdit: ('text', 'setText'),
    QDateEdit: ('dateTime.toPyDateTime', 'setDate'),
    QCheckBox: ('isChecked', 'setChecked'),
    QSpinBox: ('value', 'setValue'),
    QSlider: ('value', 'setValue'),
    QRadioButton: ('isChecked', 'setChecked')}

class FormFields(object):
    # simplify getting/setting all form field values
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        baseclass = self.__class__.__bases__[0] # eg PyQt5.QtWidgets.QTextEdit, (class object not str)
        type_ = obj_vals[baseclass]
        getter, setter = type_[0], type_[1] # currentText, setCurrentText
        f.set_self(vars())

    @property
    def val(self):
        return f.getattr_chained(self, self.getter) # chained because DateEdit needs multi method() calls

    @val.setter
    def val(self, value):
        self._set_val(value)

    def _set_val(self, value):
        getattr(self, self.setter)(value)

    def set_name(self, name):
        # give widget a unique objectName to save/restore state
        if hasattr(self, 'setObjectName'):
            self.setObjectName(f'{name}_{self.baseclass.__name__}'.replace(' ', '').lower())

class ComboBox(QComboBox, FormFields):
    def __init__(self, items=None, editable=True, *args, **kw):
        super().__init__(*args, **kw)
        self.setMaxVisibleItems(20)
        self.setEditable(editable)
        self.addItems(items)
        self.items = items
    
    @FormFields.val.setter
    def val(self, value):
        # prevent adding previous default items not in this list
        if value in self.items:
            self._set_val(value)

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
        self.setCalendarPopup(calendar)

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

