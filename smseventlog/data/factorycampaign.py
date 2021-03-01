from timeit import default_timer as timer

from bs4 import BeautifulSoup

from .. import styles as st
from ..gui import dialogs as dlgs
from .. import errors as er
from .__init__ import *

log = getlog(__name__)

# NOTE could make FCImport object to store results better

@er.errlog('Incorrect unit input', status_msg=True)
def parse_units(units : str, prefix : str = None) -> list:
    """Parse string list/range of units, add prefix

    Parameters
    ----------
    units : str
        list/range of units
    prefix : str, optional
        prefix to append to each unit, default None

    Returns
    -------
    list
        list of parsed units
    Bool
        False if unit in range cannot be converted to int

    Examples
    -------
    >>> fc.parse_units('301, 302--303', 'F')
    >>> ['F301', 'F302', 'F303']
    """

    # parse unit_range string
    units = units.split(',')

    # get upper/lower range if str has '-'
    units_range = list(filter(lambda x: '--' in x, units))
    units = list(filter(lambda x: not '--' in x, units))

    for _rng in units_range:
        rng = _rng.split('--')
        try:
            lower = int(rng[0])
            upper = int(rng[1])
        except:
            msg = f'Values for range must be integers: "{_rng.strip()}"'
            dlgs.msg_simple(msg=msg, icon='warning')
            return False

        units.extend([unit for unit in range(lower, upper + 1)])

    # strip whitespace, convert to str, add prefix
    if prefix is None: prefix = ''
    units = list(map(lambda x: f'{prefix}{str(x).strip()}', units))

    return units

def create_fc_manual(units : list, fc_number : str, _type : str, subject : str, release_date : dt, expiry_date : dt, **kw):
    """Create manual FC from input dialog"""    

    df = db.get_df_unit() \
        .pipe(lambda df: df[df.Unit.isin(units)]) \
        [['Model', 'Serial']] \
        .reset_index() \
        .assign(
            FCNumber=fc_number,
            Subject=subject,
            Classification=_type,
            StartDate=release_date,
            EndDate=expiry_date)

    import_fc(df=df, **kw)

def tblcount(tbl):
    cursor = db.cursor
    sql = f'Select count(*) From {tbl}'
    return cursor.execute(sql).fetchval()

def get_import_files():
    # load all csv files from import folder to df
    p = f.drive / f.config['FilePaths']['Import FC']
        
    lst = [f for f in p.glob('*.csv')]

    if lst:
        msg = ('Found file(s): \n\t' + 
            '\n\t'.join([p.name for p in lst]) +
            '\n\nWould you like to import?')
        if not dlgs.msgbox(msg=msg, yesno=True): return
    else:
        msg = f'No files founnd in import folder: \n\n{p}'
        dlgs.msg_simple(msg=msg, icon='Warning')
        return

    return lst

def import_fc(lst_csv=None, upload=True, df=None, worker_thread=False):   
    start = timer()

    if df is None:
        df = pd.concat([read_fc(p=p) for p in lst_csv], sort=False) \
            .drop_duplicates(['FCNumber', 'Unit'])
    
    # NOTE for now just auto filter to FCs in last 2 yrs
    d_lower = dt.now() + delta(days=-730)
    df = df[df.StartDate >= d_lower]

    if not lst_csv is None:
        print('Loaded ({}) FCs from {} file(s) in: {}s' \
            .format(len(df), len(lst_csv), f.deltasec(start, timer())))

    # import to temp staging table in db, then merge new rows to FactoryCampaign
    if upload:
        cursor = db.cursor
        df.to_sql(name='FactoryCampaignImport', con=db.engine, if_exists='append', index=False)

        msg = 'Rows read from import files: {}'.format(len(df))

        try:
            # FactoryCampaign Import
            rows = dd(int, cursor.execute('mergeFCImport').fetchall())
            msg += '\n\nFactoryCampaign: \n\tRows added: {}\n\tRows updated: {}\n\tKA Completion dates added: {}' \
                .format(
                    rows['INSERT'], 
                    rows['UPDATE'], 
                    rows['KADatesAdded'])

            # FC Summary - New rows added
            rows = dd(int, cursor.execute('MergeFCSummary').fetchall())
            if cursor.nextset():
                msg += '\n\nFC Summary: \n\tRows added: {} \n\n\t'.format(rows['INSERT'])
                df2 = f.cursor_to_df(cursor)
                if len(df2) > 0:
                    msg += st.left_justified(df2).replace('\n', '\n\t')
                    for fc_number in df2.FCNumber:
                        create_fc_folder(fc_number=fc_number)
            
            cursor.commit()
        except:
            er.log_error(log=log)
            dlgs.msg_simple(msg='Couldn\'t import FCs!', icon='critical')
        finally:
            cursor.close()

        statusmsg = 'Elapsed time: {}s'.format(f.deltasec(start, timer()))
        if worker_thread:
            return msg, statusmsg, lst_csv
        else:
            ask_delete_files(msg=msg, statusmsg=statusmsg, lst_csv=lst_csv)

def ask_delete_files(msg=None, statusmsg=None, lst_csv=None):
    if msg is None: return
    if isinstance(msg, tuple):
        # came back from worker thread # NOTE kinda ugly
        msg, statusmsg, lst_csv = msg[0], msg[1], msg[2]
        
    msg += '\n\nWould you like to delete files?'
    if dlgs.msgbox(msg=msg, yesno=True, statusmsg=statusmsg):
        for p in lst_csv: p.unlink()

def create_fc_folder(fc_number):
    try:
        p = f.drive / f.config['FilePaths']['Factory Campaigns'] / fc_number
        p.mkdir(parents=True)
    except:
        print(f'Couldn\'t make fc path for: {fc_number}')

def read_fc(p):
    """Read FC csv from KA
    - Removes units not in db
    """
    # Drop and reorder,  Don't import: CompletionSMR, claimnumber, ServiceLetterDate
    cols = ['FCNumber','Model', 'Serial', 'Unit', 'StartDate', 'EndDate', 'DateCompleteKA', 'Subject', 'Classification', 'Branch', 'Status']

    dtypes = dict(Model='object', Serial='object', Unit='object')

    dfu = db.get_df_unit()
    return pd.read_csv(p, header=5, dtype=dtypes) \
        .rename(columns=f.config['Headers']['FCImport']) \
        .pipe(f.parse_datecols) \
        .merge(right=dfu[['Model', 'Serial', 'Unit']], how='left') \
        .pipe(db.filter_database_units) \
        .reset_index(drop=True) \
        [cols]

def read_fc_old(p):
    # Raw FC data comes from KA as an html page disguised as an xls
    # TODO: Drop ServiceLetterDate > same as StartDate
    # TODO: Drop CompletionDate > changed to DateCompleteKA, Drop ClaimNumber

    with open(p) as html:
        table = BeautifulSoup(html, features='lxml').findAll('table')[2] # FC data is in 3rd table

    cols = [hdr.text for hdr in table.find('thead').find_all('th')]
    data = [[col.text for col in row.findAll('td')] for row in table.findAll('tr')[1:]]
    dfu = db.get_df_unit()

    df = pd.DataFrame(data=data, columns=cols) \
        .pipe(f.parse_datecols) \
        .merge(right=dfu[['Model', 'Serial', 'Unit']], how='left')

    # Remove missing units
    # TODO: Return these to user somehow?
    df.Unit.replace('', pd.NA, inplace=True)
    df.dropna(subset=['Unit'], inplace=True)

    # Rename Cols
    df.columns = ['FCNumber', 'Distributor', 'Branch', 'Model', 'Serial', 'Safety', 'StartDate', 'EndDate', 'Subject', 'ClaimNumber', 'CompletionSMR', 'DateCompleteKA', 'Status', 'Hours', 'ServiceLetterDate', 'Classification', 'Unit']

    # Drop and reorder,  Don't import: CompletionSMR, claimnumber, ServiceLetterDate
    cols = ['FCNumber','Model', 'Serial', 'Unit', 'StartDate', 'EndDate', 'DateCompleteKA', 'Subject', 'Classification', 'Hours', 'Distributor', 'Branch',  'Safety', 'Status']
    df = df[cols]

    df.FCNumber = df.FCNumber.str.strip()

    return df

def import_ka():
    # One time import of machine info from mykomatsu
    p = Path('C:/Users/jayme/OneDrive/Desktop/KA Machine Info')
    lst = [f for f in p.glob('*.html')]

    df = pd.concat([read_ka(p=p) for p in lst], sort=False).reset_index(drop=True)

    return df

def read_ka(p):
    with open(p) as html:
        table = BeautifulSoup(html).findAll('table')[1]

    cols = ['Unit', 'Model', 'Serial', 'LastSMR']
    data = [[col.text.replace('\n', '').replace('\t', '') for col in row.findAll('td')[2:6]] for row in table.findAll('tr')]
    df = pd.DataFrame(data=data, columns=cols)
    df = df[df.Serial.str.len()>2].reset_index(drop=True)
    df.LastSMR = pd.to_datetime(df.LastSMR, format='%m/%d/%Y %H:%M %p')

    return df

def update_scheduled_db(df, **kw):
    """Update cleaned df scheduled status in FactoryCampaign db table

    Parameters
    ----------
    df : pd.DataFrame
        cleaned df
    """    
    from .. import dbtransaction as dbt
    from ..utils.dbmodel import FactoryCampaign

    dbt.DBTransaction(dbtable=FactoryCampaign, table_view=False, **kw) \
        .add_df(df=df, update_cols='Scheduled') \
        .update_all()

def update_scheduled_excel(df, scheduled=True):
    """Update "Scheduled" status in FactoryCampaign

    Parameters
    ----------
    df : pd.DataFrame
        df from "SAP Notification Duplicator" table, copied from clipboard
    scheduled : bool
        update FCs to be scheduled or not, default True

    Examples
    --------
    >>> df = pd.read_clipboard()
    >>> fc.update_scheduled(df=df)
    """   

    # parse FC number from title
    # NOTE may need to replace prefixes other than 'FC' eg 'PSN'
    df = df \
        .pipe(f.lower_cols) \
        .dropna() \
        .assign(
            Unit=lambda x: x.unit.str.replace('F0', 'F'),
            FCNumber=lambda x: x.title.str.split(' - ', expand=True)[1] \
                .str.replace('FC', '') \
                .str.replace('PSN', '') \
                .str.strip(),
            Scheduled=scheduled) \
        [['Unit', 'FCNumber', 'Scheduled']]

    update_scheduled_db(df=df)

def update_scheduled_sap(df=None, exclude=None, **kw):
    """Update scheduled fc status from sap data
    - copy table in sap, then this func will read clipboard
    - NOTE rejected notifications get status COMP

    Parameters
    ----------
    df : pd.DataFrame
        df, default None
    kw :
        used here to pass active table widget to dbtxn for update message
    
    Examples
    --------
    >>> fc.update_scheduled_sap(exclude=['SMSFH-008'])
    """
    if exclude is None:
        exclude = []

    # if exclude vals came from gui dialog
    if isinstance(exclude, tuple):
        ans = exclude[0] # 1 or 0 for dialog accept/reject
        exclude = exclude[1] if ans == 1 else []
    
    # split string items to list
    if isinstance(exclude, str):
        exclude = [item.strip() for item in exclude.split(',')]

    df_fc = db.get_df_fc(default=False)

    # read df data from clipboard
    if df is None:
        cols = ['notification', 'order', 'pg', 'title', 'sort', 'floc', 'status', 'date_changed', 'changed_by', 'p', 'typ', 'date_created', 'report_by', 'workctr']
        df = pd.read_clipboard(names=cols, header=None) \
            .pipe(f.parse_datecols)

    # extract FCNumber from description with regex expr matching FC or PSN then fc_number
    # F0314 FC[19H055-1] CHANGE STEERING BRACKET
    # F0314 PSN[ 19H055-1] CHANGE STEERING BRACKET
    # https://stackoverflow.com/questions/20089922/python-regex-engine-look-behind-requires-fixed-width-pattern-error
    expr = r'(?:(?<=FC)|(?<=PSN))(\s*[^\s]+)'
    expr2 = r'^[^a-zA-Z0-9]+' # replace non alphanumeric chars at start of string eg '-'

    # set Scheduled=True for any rows which dont have 'RJCT'
    df = df \
        .assign(
            FCNumber=lambda x: x.title \
                .str.extract(expr, flags=re.IGNORECASE)[0] \
                .str.strip() \
                .str.replace(expr2, ''),
            Unit=lambda x: x.floc \
                .str.split('-', expand=True)[0] \
                .str.replace('F0', 'F'),
            Scheduled=lambda x: ~x.status.str.contains('RJCT')) \
        .sort_values(by=['Unit', 'FCNumber', 'date_created'], ascending=[True, True, False]) \
        .drop_duplicates(subset=['Unit', 'FCNumber'], keep='first') \
        .pipe(lambda df: df[~df.FCNumber.isin(exclude)]) \
        .pipe(lambda df: df[df.FCNumber.isin(df_fc['FC Number'])]) \
        [['Unit', 'FCNumber', 'Scheduled']]

    # return df
    update_scheduled_db(df=df, **kw)