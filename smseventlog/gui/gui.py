from ..utils.credentials import CredentialManager
from ..data.units import update_comp_smr
from . import _global as gbl
from . import dialogs as dlgs
from . import multithread as mlt
from . import tables as tbls
from .__init__ import *
from .multithread import Worker
from .update import Updater

log = getlog(__name__)

# FEATURES NEEDED
# TODO Keyboard shortcuts > ctrl + down, right
# TODO save previous query and run when tab first selected

class MainWindow(QMainWindow):
    minesite_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.app = QApplication.instance()
        self.setWindowTitle(gbl.title)
        self.setMinimumSize(QSize(1000, 400))
        self.minesite_changed.connect(self.update_minesite_label)
        self.minesite_label = QLabel(self) # permanent label for status bar so it isnt changed by statusTips
        self.minesite_label.setToolTip('Global MineSite > Set with [Ctrl + Shift + M]')
        self.rows_label = QLabel(self)
        self.statusBar().addPermanentWidget(self.rows_label)
        self.statusBar().addPermanentWidget(self.minesite_label)

        # Settings
        s = QSettings('sms', 'smseventlog', self)
        self.resize(s.value('window size', defaultValue=QSize(1200, 1000)))
        self.move(s.value('window position', defaultValue=QPoint(50, 50)))
        self.minesite = s.value('minesite', defaultValue='FortHills')
        self.settings = s

        self.create_actions()
        self.create_menu()

        self.tabs = TabWidget(self)
        self.setCentralWidget(self.tabs)
        self.update_minesite_label()

        self.threadpool = QThreadPool(self)
        log.debug('Mainwindow init finished.')
    
    @property
    def minesite(self):
        return self._minesite

    @minesite.setter
    def minesite(self, val):
        self._minesite = val
        self.minesite_changed.emit(val)
    
    def update_minesite_label(self, *args):
        """minesite_label is special label to always show current minesite (bottom right)"""
        self.minesite_label.setText(f'Minesite: {self.minesite}')
    
    def update_rows_label(self, *args):
        view = self.active_table()
        if view is None:
            return # not init yet

        model = view.model()
        visible_rows = model.visible_rows
        total_rows = model.total_rows

        if total_rows == visible_rows:
            num_rows = visible_rows
        else:
            num_rows = f'{visible_rows}/{total_rows}'

        self.rows_label.setText(f'Rows: {num_rows}')
    
    def warn_not_implemented(self):
        self.update_statusbar('Warning: This feature not yet implemented.')
    
    def update_statusbar(self, msg=None, warn=False, success=False, log_=False, *args):
        """Statusbar shows temporary messages that disappear on any context event"""
        if not msg is None:

            # allow warn or success status to be passed with msg as dict
            if isinstance(msg, dict):
                warn = msg.get('warn', False)
                success = msg.get('success', False)
                msg = msg.get('msg', None) # kinda sketch

            if log_:
                log.info(msg)

            bar = self.statusBar()
            self.prev_status = bar.currentMessage()
            bar.showMessage(msg)

            msg_lower = msg.lower()
            if warn or 'warn' in msg_lower or 'error' in msg_lower:
                color = '#ff5454' # '#fa7070'
            elif success or 'success' in msg_lower:
                color = '#70ff94'
            else:
                color = 'white'

            palette = bar.palette()
            palette.setColor(QPalette.Foreground, QColor(color))
            bar.setPalette(palette)

            self.app.processEvents()
    
    def revert_status(self):
        # revert statusbar to previous status
        if not hasattr(self, 'prev_status'):
            self.prev_status = ''

        self.update_statusbar(msg=self.prev_status)

    @er.errlog()
    def after_init(self):
        """Steps to run before MainWindow is shown.
        - Everything in here must suppress errors and continue"""
        self.username = self.get_username()
        self.init_sentry()

        self.u = users.User(username=self.username, mainwindow=self).login()
        log.debug('user init')

        last_tab_name = self.settings.value('active table', 'Event Log')
        self.tabs.init_tabs()
        self.tabs.activate_tab(title=last_tab_name)
        log.debug('last tab activated')

        # initialize updater
        self.updater = Updater(mw=self, dev_channel=self.get_setting('dev_channel'))
        log.debug(f'updater initialized, channel={self.updater.channel}')

        self.active_table_widget().refresh(default=True)
        log.debug('last table refreshed')

        self.check_update()
        self.start_update_timer()
        log.debug('Finished after_init')
    
    def start_update_timer(self, mins=180):
        # check for updates every 3 hrs
        if not SYS_FROZEN: return

        msec = mins * 60 * 1000

        self.update_timer = QTimer(parent=self)
        self.update_timer.timeout.connect(self.check_update)
        self.update_timer.start(msec)

    @er.errlog('Failed to check for update!', display=True)
    def check_update(self, *args):
        """Check for update and download in a worker thread"""
        if not SYS_FROZEN:
            self.update_statusbar('App not frozen, not checking for updates.')
            return

        if self.updater.update_available:
            # update has been previously checked and downloaded but user declined to install initially
            self._install_update(updater=self.updater)
        else:
            Worker(func=self.updater.check_update, mw=self) \
                .add_signals(signals=('result', dict(func=self._install_update))) \
                .start()
    
    def _install_update(self, updater=None, ask_user=True):
        if updater is None: return

        # prompt user to install update and restart
        msg = f'An updated version of the Event Log is available.\n\n\
            Current: {updater.version}\n\
            Latest: {updater.latest_version}\n\n\
            Would you like to restart and update now?'

        if ask_user:
            if not dlgs.msgbox(msg=msg, yesno=True): return

        Worker(func=updater.install_update, mw=self).start()
        self.update_statusbar('Extracting update and restarting...')

    def init_sentry(self):
        """Add user-related scope information to sentry"""
        with configure_scope() as scope:
            scope.user = dict(
                username=self.username,
                email=self.get_setting('email'))
            # scope.set_extra('version', VERSION) # added to sentry release field
                
    def active_table_widget(self):
        return self.tabs.currentWidget()
       
    def active_table(self):
        table_widget = self.active_table_widget()
        if not table_widget is None:
            return table_widget.view
    
    def show_changeminesite(self):
        dlg = dlgs.ChangeMinesite(parent=self)
        return dlg.exec_()
        
    @er.errlog('Close event failed.')
    def closeEvent(self, event):
        s = self.settings
        s.setValue('window size', self.size())
        s.setValue('window position', self.pos())
        s.setValue('screen', self.geometry().center())
        s.setValue('minesite', self.minesite)
        s.setValue('active table', self.active_table_widget().title)

        # update on closeEvent if update available... maybe not yet
        # if self.updater.update_available:
        #     self._install_update(updater=self.updater, ask_user=False)
    
    def get_setting(self, key, default=None):
        val = self.settings.value(key, defaultValue=default)
        if isinstance(val, str) and val.strip() == '':
            return default
        
        # windows bool settings saved as strings eg 'true'
        if val in ('true', 'false'):
            val = f.str_to_bool(val)
        
        return val
    
    def get_username(self):
        s = self.settings
        username = self.get_setting('username')
        email = self.get_setting('email')

        if username is None or email is None:
            self.set_username()
            username = self.username

        return username
    
    def set_username(self):
        # show username dialog and save first/last name to settings
        s = self.settings
        dlg = dlgs.InputUserName(self)
        if not dlg.exec_(): return

        s.setValue('username', dlg.username)
        s.setValue('email', dlg.email)
        self.username = dlg.username

        if hasattr(self, 'u'):
            self.u.username = dlg.username
            self.u.email = dlg.email

    def set_tsi_username(self):
        CredentialManager('tsi').prompt_credentials()
               
    @property
    def driver(self):
        return self._driver if hasattr(self, '_driver') else None

    @driver.setter
    def driver(self, driver):
        self._driver = driver
            
    def open_sap(self):
        from ..utils.web import SuncorWorkRemote
        self.sc = SuncorWorkRemote(mw=self, _driver=self.driver)

        Worker(func=self.sc.open_sap, mw=self) \
            .add_signals(signals=('result', dict(func=self.handle_sap_result))) \
            .start()
        self.update_statusbar('Opening SAP...')
    
    def handle_sap_result(self, sc=None):
        # just need to keep a referece to the driver in main thread so chrome doesnt close
        if sc is None: return
        self.driver = sc.driver
        self.update_statusbar('SAP started.', success=True)

    def create_menu(self):
        bar = self.menuBar()

        file_ = bar.addMenu('File')
        file_.addAction(self.act_new_item)
        file_.addSeparator()
        file_.addAction(self.act_refresh)
        file_.addAction(self.act_refresh_allopen)
        file_.addAction(self.act_reload_lastquery)
        file_.addSeparator()
        file_.addAction(self.act_prev_tab)
        file_.addAction(self.act_change_minesite)
        file_.addAction(self.act_viewfolder)
        file_.addSeparator()
        menu_reports = file_.addMenu('Reports')
        menu_reports.addAction(self.act_fleet_monthly_report)
        menu_reports.addAction(self.act_fc_report)
        menu_reports.addSeparator()
        menu_reports.addAction(self.act_plm_report)
        menu_reports.addAction(self.act_import_plm_manual)

        edit_ = bar.addMenu('Edit')
        edit_.addAction(self.act_find)
        edit_.addAction(self.act_paste_date)
        
        table_ = bar.addMenu('Table')
        table_.addAction(self.act_email_table)
        table_.addAction(self.act_export_excel_table)
        table_.addAction(self.act_export_csv_table)       
        table_.addSeparator()
        table_.addAction(self.act_toggle_color)
        table_.addAction(self.act_jump_rows)

        rows_ = bar.addMenu('Rows')
        rows_.addAction(self.act_open_tsi)
        rows_.addAction(self.act_delete_event)
        rows_.addAction(self.act_update_component)
        rows_.addAction(self.act_detailsview)
        rows_.addAction(self.act_get_wo)

        database_ = bar.addMenu('Database')
        database_.addAction(self.act_update_comp_smr)
        database_.addAction(self.act_update_fc_status_clipboard)
        database_.addSeparator()
        database_.addAction(self.act_reset_db)
        database_.addAction(self.act_reset_db_tables)
        database_.addSeparator()
        database_.addAction(self.act_open_sap)

        help_ = bar.addMenu('Help')
        help_.addAction(self.act_show_about) # this actually goes to main 'home' menu
        help_.addAction(self.act_check_update)
        help_.addAction(self.act_email_err_logs)
        help_.addAction(self.act_enable_disable_dev)
        help_.addSeparator()
        help_.addAction(self.act_username)
        help_.addAction(self.act_tsi_creds)
        help_.addAction(self.act_sms_creds)
        help_.addAction(self.act_exchange_creds)
        help_.addAction(self.act_sap_creds)

    def create_actions(self):
        # Menu/shortcuts
        t, tv = self.active_table_widget, self.active_table

        act_show_about = QAction('About', self, triggered=dlgs.about)
        act_open_sap = QAction('Open SAP', self, triggered=self.open_sap)
        act_check_update = QAction('Check for Update', self, triggered=self.check_update)
        act_email_err_logs = QAction('Email Error Logs', self, triggered=self.email_err_logs)
        act_enable_disable_dev = QAction('Enable/Disable Dev Channel', self, triggered=self.enable_disable_dev)

        # Reports
        act_fleet_monthly_report = QAction('Fleet Monthly Report', self, triggered=lambda: self.create_monthly_report('Fleet Monthly'))
        act_plm_report = QAction('PLM Report', self, triggered=self.create_plm_report)
        act_import_plm_manual = QAction('Import PLM Records', self, triggered=self.import_plm_manual)
        act_fc_report = QAction('FC Report', self, triggered=lambda: self.create_monthly_report('FC'))
        
        # Reset credentials
        act_username = QAction('Reset Username', self, triggered=self.set_username)
        act_tsi_creds = QAction('Reset TSI Credentials', self,
            triggered=lambda: CredentialManager('tsi').prompt_credentials())
        act_sms_creds = QAction('Reset SMS Credentials', self,
            triggered=lambda: CredentialManager('sms').prompt_credentials())
        act_exchange_creds = QAction('Reset Exchange Credentials', self,
            triggered=lambda: CredentialManager('exchange').prompt_credentials())
        act_sap_creds = QAction('Reset SAP Credentials', self,
            triggered=lambda: CredentialManager('sap').prompt_credentials())

        act_refresh = QAction('Refresh Menu', self,
            triggered=lambda: t().show_refresh(),
            shortcut=QKeySequence('Ctrl+R'))
        act_new_item = QAction('Add New Row', self,
            triggered=lambda: t().show_addrow(),
            shortcut=QKeySequence('Ctrl+Shift+N'))

        act_prev_tab = QAction('Previous Tab', self,
            triggered=lambda: self.tabs.activate_previous(),
            shortcut=QKeySequence('Meta+Tab'))

        act_change_minesite = QAction('Change MineSite', self,
            triggered=self.show_changeminesite,
            shortcut=QKeySequence('Ctrl+Shift+M'))
        act_paste_date = QAction('Insert Current Date', self,
            triggered=self.paste_date,
            shortcut=QKeySequence('Ctrl+Shift+D'))
        

        act_open_tsi = QAction('Open TSI', self, triggered=self.open_tsi)
        act_delete_event = QAction('Delete Row', self, triggered=lambda: t().remove_row())

        act_update_comp_smr = QAction('Update Component SMR', self, triggered=update_comp_smr)
        act_reset_db = QAction('Reset Database Connection', self, triggered=db.reset)
        act_reset_db_tables = QAction('Reset Database Tables', self, triggered=db.clear_saved_tables)

        act_reload_lastquery = QAction('Reload Last Query', self, 
            triggered=lambda: t().refresh(last_query=True),
            shortcut=QKeySequence('Ctrl+Shift+L'))
        act_refresh_allopen = QAction('Refresh All Open', self, 
            triggered=lambda: t().refresh_allopen(default=True),
            shortcut=QKeySequence('Ctrl+Shift+R'))
        act_refresh_lastweek = QAction('Refresh Last Week', self, 
            triggered=lambda: t().refresh_lastweek(base=True))
        act_refresh_lastmonth = QAction('Refresh Last Month', self, 
            triggered=lambda: t().refresh_lastmonth(base=True))

        act_viewfolder = QAction('View Folder', self,
            triggered=lambda: t().view_folder(),
            shortcut=QKeySequence('Ctrl+Shift+V'))

        act_detailsview = QAction('Details View', self,
            triggered=lambda: t().show_details(),
            shortcut=QKeySequence('Ctrl+Shift+D'))
        act_jump_rows = QAction('Jump First/Last Row', self,
            triggered=lambda: tv().jump_top_bottom(),
            shortcut=QKeySequence('Ctrl+Shift+J'))
        
        act_get_wo = QAction('Get WO from email', self,
            triggered=lambda: t().get_wo_from_email())

        act_update_component = QAction('Update Component', self,
            triggered=lambda: t().show_component())
        act_update_fc_status_clipboard = QAction('Update FC Status Clipboard', self,
            triggered=lambda: fc.update_scheduled_sap(
                exclude=dlgs.inputbox(
                    msg='1. Enter FCs to exclude\n2. Copy FC Data from SAP to clipboard\n\nExclude:'),
                table_widget=t()))
        act_email_table = QAction('Email Table', self, 
            triggered=lambda: t().email_table())
        act_export_excel_table = QAction('Export to Excel', self,
            triggered=lambda: t().export_df('xlsx'))
        act_export_csv_table = QAction('Export to csv', self,
            triggered=lambda: t().export_df('csv'))
        act_toggle_color = QAction('Toggle Color', self,
            triggered=lambda: tv().model().toggle_color())

        act_update_smr = QAction('Update SMR', self,
            triggered=lambda: t().update_smr())
        act_update_smr.setToolTip('Update selected event with SMR from database.')
        act_show_smr_history = QAction('Show SMR History', self,
            triggered=lambda: t().show_smr_history())

        act_find = QAction('Find', self,
            triggered=lambda: tv().show_search(),
            shortcut=QKeySequence('Ctrl+F'))

        f.set_self(vars())

    def contextMenuEvent(self, event):
        """Add actions to right click menu, dependent on currently active table
        """
        child = self.childAt(event.pos())

        menu = QMenu(self)
        # menu.setToolTipsVisible(True)

        table_widget = self.active_table_widget()
        for section in table_widget.context_actions.values():
            for action in section:
                name_action = f'act_{action}'
                try:
                    menu.addAction(getattr(self, name_action))
                except:
                    try:
                        menu.addAction(getattr(table_widget, name_action))
                    except:        
                        log.warning(f'Couldn\'t add action to context menu: {action}')
            
            menu.addSeparator()

        action = menu.exec_(self.mapToGlobal(event.pos()))

    def open_tsi(self):
        # NOTE should probs move to table_widget
        view = self.active_table()
    
        if not view.parent.title in ('Event Log', 'Work Orders', 'Component CO'):
            msg = 'Please chose a row from the Event Log or Work Orders tab.'
            dlgs.msg_simple(msg=msg, icon='warning')
            return

        e, row = view.e, view.row
        if row is None: return

        row.update(vals=dict(StatusTSI='Open', TSIAuthor=self.username))
        self.update_statusbar(msg=f'TSI opened for: {e.Unit} - {e.Title}', success=True)
    
    def create_monthly_report(self, name : str):
        """Create report in worker thread from dialog menu

        Parameters
        ----------
        name : str
            ['Fleet Monthly', 'FC']
        """        

        dlg = dlgs.BaseReportDialog(window_title=f'{name} Report')
        if not dlg.exec_():
            return

        from ..reports import FleetMonthlyReport, FCReport
        Report = {
            'Fleet Monthly': FleetMonthlyReport,
            'FC': FCReport}.get(name)

        rep = Report(
            d=dlg.d,
            minesite=dlg.items['MineSite'])

        Worker(func=rep.create_pdf, mw=self) \
            .add_signals(signals=('result', dict(func=self.handle_monthly_report_result))) \
            .start()

        self.update_statusbar('Creating Fleet Monthly Report...')

    def handle_monthly_report_result(self, rep=None):
        if rep is None: return
        fl.open_folder(rep.p_rep)

        msg = f'Report:\n\n"{rep.title}"\n\nsuccessfully created. Email now?'
        if dlgs.msgbox(msg=msg, yesno=True):
            rep.email()

    def import_plm_manual(self):
        """Allow user to manually select haulcycle files to upload"""
        t = self.active_table_widget()
        e = t.e
        if not e is None:
            from .. import eventfolders as efl
            unit, dateadded = e.Unit, e.DateAdded
            uf = efl.UnitFolder(unit=unit)
            p = uf.p_unit
        else:
            # No unit selected, try to get minesite equip path
            p = f.drive / f.config['EquipPaths'].get(self.minesite.replace('-', ''), '')
        
        if p is None:
            p = Path.home() / 'Desktop'

        lst_csv = dlgs.get_filepaths(p_start=p)
        if not lst_csv:
            return # user didn't select anything
        
        from ..data.internal import plm
        Worker(func=plm.import_plm_csv, mw=self, lst_csv=lst_csv) \
            .add_signals(('result', dict(func=self.handle_import_result_manual))) \
            .start()
        
        self.update_statusbar('Importing haul cylce files from network drive (this may take a few minutes)...')
    
    def create_plm_report(self):
        """Trigger plm report from current unit selected in table"""
        from ..data.internal import plm

        view = self.active_table()
        try:
            e = view.e
            unit, d_upper = e.Unit, e.DateAdded
        except er.NoRowSelectedError:
            # don't set dialog w unit and date, just default
            unit, d_upper, e = None, None, None
        
        # Report dialog will always set final unit etc
        dlg = dlgs.PLMReport(unit=unit, d_upper=d_upper)
        ok = dlg.exec_()
        if not ok:
            return # user exited

        m = dlg.get_items(lower=True) # unit, d_upper, d_lower

        # check if unit selected matches event selected
        if not e is None:
            if not e.Unit == m['unit']:
                e = None

        m['e'] = e
        # NOTE could make a func 'rename_dict_keys'
        m['d_upper'], m['d_lower'] = m['date upper'], m['date lower']

        # check max date in db
        query = qr.PLMUnit(**m)
        maxdate = query.max_date()
        if maxdate is None: maxdate = dt.now() + delta(days=-731)

        if maxdate + delta(days=5) < m['d_upper']:
            # worker will call back and make report when finished
            if not fl.drive_exists(warn=False):
                msg = 'Can\'t connect to P Drive. Create report without updating records first?'
                if dlgs.msgbox(msg=msg, yesno=True):
                    self.make_plm_report(**m)

                return

            Worker(func=plm.update_plm_single_unit, mw=self, unit=m['unit']) \
                .add_signals(
                    signals=('result', dict(
                        func=self.handle_import_result,
                        kw=m))) \
                .start()

            msg = f'Max date in db: {maxdate:%Y-%m-%d}. Importing haul cylce files from network drive, this may take a few minutes...'
            self.update_statusbar(msg=msg)

        else:
            # just make report now
            self.make_plm_report(**m)
    
    def handle_import_result_manual(self, rowsadded=None, **kw):
        if not rowsadded is None:
            msg = dict(msg=f'PLM records added to database: {rowsadded}', success=rowsadded > 0)
        else:
            msg = 'Warning: Failed to import PLM records.'

        self.update_statusbar(msg)
    
    def handle_import_result(self, m_results=None, **kw):
        if m_results is None: return

        rowsadded = m_results['rowsadded']
        self.update_statusbar(f'PLM records added to database: {rowsadded}', success=True)

        self.make_plm_report(**kw)

    def make_plm_report(self, e=None, **kw):
        """Actually make the report pdf"""
        from .. import eventfolders as efl
        from ..reports import PLMUnitReport
        rep = PLMUnitReport(mw=self, **kw)

        if not e is None:
            ef = efl.EventFolder.from_model(e)
            p = ef._p_event
        else:
            ef = None

        # If cant get event folder, ask to create at desktop
        if ef is None or not ef.check(check_pics=False, warn=False):
            p = Path.home() / 'Desktop'
            msg = f'Can\'t get event folder, create report at desktop?'
            if not dlgs.msgbox(msg=msg, yesno=True):
                return
        
        Worker(func=rep.create_pdf, mw=self, p_base=p) \
            .add_signals(signals=('result', dict(func=self.handle_plm_result, kw=kw))) \
            .start()

        self.update_statusbar(f'Creating PLM report for unit {kw["unit"]}...')
    
    def handle_plm_result(self, rep=None, unit=None, **kw):
        if rep is False:
            # not super robust, but just warn if no rows in query
            msg = f'No rows returned in query, can\'t create report!'
            dlgs.msg_simple(msg=msg, icon='warning')

        if not rep or not rep.p_rep.exists():
            self.update_statusbar('Failed to create PLM report.', warn=True)
            return

        self.update_statusbar(f'PLM report created for unit {unit}', success=True)

        msg = f'Report:\n\n"{rep.title}"\n\nsuccessfully created. Open now?'
        if dlgs.msgbox(msg=msg, yesno=True):
            fl.open_folder(rep.p_rep)

    def email_err_logs(self):
        """Collect and email error logs to simplify for user"""
        docs = []
        def _collect_logs(p):
            return [p for p in p.glob('*log*')] if p.exists() else []
                
        # collect sms logs
        p_sms = f.applocal / 'logging'
        docs.extend(_collect_logs(p_sms))

        # collect pyupdater logs
        i = 1 if f.is_win() else 0
        p_pyu = f.applocal.parents[1] / 'Digital Sapphire/PyUpdater/logs'
        docs.extend(_collect_logs(p_pyu))

        from ..utils import email as em

        subject = f'Error Logs - {self.username}'
        body = 'Thanks Jayme,<br><br>I know you\'re trying your best. The Event Log is amazing and we appreciate all your hard work!'
        msg = em.Message(subject=subject, body=body, to_recip=['jgordon@smsequip.com'], show_=False)
        msg.add_attachments(docs)
        msg.show()

    def paste_date(self):
        # TODO not implemented yet
        d = dt.now().strftime('%Y-%m-%d')
        return

    def enable_disable_dev(self):
        """Enable or disable development channel setting
        - Enabled means user will get alpha updates"""
        name = 'dev_channel'
        val = not self.get_setting(name, False) # flip true/false
        print('dev_channel:', val)

        self.settings.setValue(name, val)
        self.update_statusbar(f'Development channel enabled: {val}', success=True, log_=True)

class TabWidget(QTabWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.tabindex = dd(int)
       
        self.prev_index = self.currentIndex()
        self.current_index = self.prev_index
        self.mainwindow = parent
        self.m_table = f.config['TableName']['Class'] # get list of table classes from config
        self.m_table_inv = f.inverse(self.m_table)
        
        self.is_init = False

        self.currentChanged.connect(self.save_activetab)
        self.currentChanged.connect(self.mainwindow.update_rows_label)

    def init_tabs(self):
        """Add all tabs to widget"""
        u = self.mainwindow.u
        lst = ['EventLog', 'WorkOrders', 'TSI', 'ComponentCO', 'ComponentSMR', 'UnitInfo', 'FCSummary', 'FCDetails', 'EmailList', 'Availability', 'OilSamples']

        # Hide specific tabs per usergroup/domain
        m_hide = dict(
            CED=['FCSummary', 'FCDetails', 'Availability'])
               
        hide = m_hide.get(u.domain, [])
        lst = [item for item in lst if not item in hide]

        lst_admin = ['UserSettings']
        if u.admin:
            lst.extend(lst_admin)

        for i, name in enumerate(lst):
            self.init_tab(name=name, i=i)
        
        self.is_init = True
    
    def init_tab(self, name=None, title=None, i=0):
        """Init tab """

        # init with either 'EventLog' or 'Event Log'
        if title is None:
            title = self.m_table.get(name, None)
        elif name is None:
            name = self.m_table_inv.get(title, None)

        if name is None or title is None:
            log.warning('Missing name or title, can\'t init tab.')
            return

        if title in self.tabindex: return # tab already init

        table_widget = getattr(tbls, name)(parent=self)
        self.insertTab(i, table_widget, title)
        self.tabindex[title] = i

    def get_index(self, title : str) -> int:
        """Return index number of table widget by title"""
        return self.tabindex[title]
    
    def get_widget(self, title : str) -> QTableWidget:
        """Return table widget by title"""
        i = self.get_index(title)
        return self.widget(i)
    
    def activate_tab(self, title : str):
        """Activate table widget by title"""
        i = self.get_index(title)
        self.setCurrentIndex(i)
    
    def save_activetab(self, *args):
        if not self.is_init: return
        s = self.parent().settings
        s.setValue('active table', self.currentWidget().title)
        
        # keep track of previous indexes for ctrl+tab to revert
        self.prev_index = self.current_index
        self.current_index = self.currentIndex()
    
    def activate_previous(self):
        self.setCurrentIndex(self.prev_index)
