from .__init__ import *
from .. import queries as qr
from .. import eventfolders as efl
from ..utils import fileops as fl

class ComponentCOConditions(qr.ComponentCOBase):
    def __init__(self, d_lower=None, components=None, minesite='FortHills', **kw):
        super().__init__(**kw)
        a, b, c = self.a, self.b, self.c

        self.cols = [a.UID, a.Unit, a.Title, a.WorkOrder, c.Component, c.Modifier, a.DateAdded, a.SMR, a.ComponentSMR, a.Floc]

        if d_lower is None:
            d_lower = dt(2020,4,1)

        if components is None:
            components = ['Spindle', 'Front Suspension', 'Rear Suspension', 'Steering Cylinder']
    
        self.fltr \
            .add(ct=a.DateAdded>=d_lower) \
            .add(ct=c.Component.isin(components)) \
            .add(ct=a.MineSite==minesite)

    def set_default_filter(self):
        self.set_minesite()

def get_condition_reports(d_lower=None):
    # query all component CO records
    query = ComponentCOConditions(minesite='FortHills')
    df_comp = db.get_df_component()
    df = query.get_df().merge(right=df_comp[['Floc', 'Combined']], how='left', on='Floc') \
        .set_index('UID', drop=False)

    pdfs = []

    # loop dataframe and check/get condition report pdfs
    for row in df.itertuples():
        ef = efl.EventFolder.from_model(e=row)
        ef.check(check_pics=False)
        df.loc[row.UID, 'HasReport'] = str(ef.condition_reports[0]) if ef.has_condition_report else False

        pdfs.extend(ef.condition_reports)
    
    # save excel file of data
    p = Path.home() / 'Desktop/condition_reports.xlsx'
    df.to_excel(p, index=False)

    # copy all condition reports to folder
    p_dst = Path.home() / 'desktop/Condition Reports'
    for p in pdfs:
        fl.copy_file(p_src=p, p_dst=p_dst / p.name)

    return df, pdfs

def get_reman_db_path():
    """Check Mehdi's reman db copy folder for newest .accdb
    - Reading 170mb file from p drive is really slow, just copy to desktop first"""
    p = Path(f.config['FilePaths']['RemanDB'])
    return list(p.rglob('*.accdb'))[0]

def load_stupid_fucking_reman_db(p=None):
    if p is None:
        p = get_reman_db_path()

    # smswo is reman internal wo
    
    cols = ['rep_date', 'rec_date', 'branch', 'customer', 'unit_num', 'model', 'machine_ser', 'component', 'comp_loc', 'comp_serial', 'machine_hrs', 'comp_hrs', 'report_type', 'smswo', 'branch_wo', 'origination', 'work_type', 'comp_issue']

    m_cols = dict(
        smswo='reman_wo',
        unit_num='unit',
        machine_ser='unit_serial')

    df = fl.read_access_database(p=p, table_name='CondRepTbl', index_col='ID') \
        [cols] \
        .rename(columns=m_cols) \
        .assign(
            branch_wo=lambda x: split_wo(x.branch_wo),
            reman_wo=lambda x: split_wo(x.reman_wo))

    return df

def import_basemine_components(p=None):
    """Read OSB component db, fix cols/values, import to db"""

    # get min UID from db, decrement from there
    sql = 'SELECT Min(UID) From EventLog'
    uid_min = db.cursor.execute(sql).fetchval() - 1

    df = load_basemine_componennt_db(p=p) \
        .assign(
            UID=lambda x: np.arange(uid_min - x.shape[0], uid_min),
            DateCompleted=lambda x: x.DateAdded,
            CreatedBy='osb_import',
            StatusEvent='Complete',
            StatusWO='Closed',
            COConfirmed=True,
            ComponentCO=True)
    
    join_cols = ['Unit', 'Floc', 'DateAdded']
    return db.insert_update(a='EventLog', b='OSBComponentImport', join_cols=join_cols, df=df)

def load_basemine_componennt_db(p=None):
    if p is None:
        p = f.config['FilePaths']['BaseMineCompDB']
    
    # convert cols to int dtype
    int_cols = ['unit', 'client_wo', 'machine_hr', 'cmpt_hr', 'transaction_hour', 'warranty_hours']
    m_dtype = {col: pd.Int64Dtype() for col in int_cols}

    df = fl.read_access_database(p=p, table_name='Sun_CO_Records', index_col='ID') \
        .pipe(f.set_default_dtypes, m=m_dtype) \
        .assign(
            unit=lambda x: x.unit.astype(str)) \
        .pipe(convert_basemine_component)

    return df

def convert_basemine_component(df):
    """Convert component types and column names before import to db"""
    m_conv = dict(
        customer={'Suncor Energy Inc.': 'Suncor'},
        component={
            'Front Strut': 'Front Suspension',
            'Wheel': 'Spindle',
            'Hoist Cyl': 'Hoist Cylinder',
            'Main Alternator': 'Traction Alternator',
            'Rear Strut': 'Rear Suspension',
            'Steering Cyl': 'Steering Cylinder',
            'Rad': 'Radiator',
            'Wheel Motor': 'Wheel Motor Transmission',
            'Tie-Rod Assy': 'Tie Rod',
            'Arc Chutes': 'Arc Chute',
            'Blower Motor': 'Grid Blower Motor',
            'Contactor': 'RP Contactor',
            'Flow Amp': 'Flow Amplifier',
            'Positive Inverter': 'IGBT Inverter',
            'Steering cyl': 'Steering Cylinder'},
        modifier={
            'LF': 'LH',
            'RF': 'RH',
            'LR': 'LH',
            'RR': 'RH',
            'Inner': 'IN',
            'Outer': 'OUT'},
        warranty={
            'NO': 'No',
            'YES': 'Yes'},
        group_co={
            'NO': False,
            np.NaN: False,
            'YES': True},
        sun_co_reason={
            'C/O AS A GRP': 'Convenience',
            'TRANSFER': 'Transfer'}
    )

    m_cols = dict(
        unit='Unit',
        install_date='DateAdded',
        component='Component',
        modifier='Modifier',
        cmpt_sn='SNInstalled',
        sms_wo='WorkOrder',
        client_wo='SuncorWO',
        po='SuncorPO',
        machine_hr='SMR',
        cmpt_hr='ComponentSMR',
        part_num='PartNumber',
        notes='RemovalReason',
        cap_usd='CapUSD',
        warranty='WarrantyYN',
        sun_co_reason='SunCOReason',
        group_co='GroupCO')

    # merge floc
    df_comp = db.get_df_component() \
        .pipe(lambda df: df[df.EquipClass=='Truck_Electric']) \
        [['Component', 'Modifier', 'Floc', 'Combined']]

    return df \
        .replace(m_conv) \
        [m_cols] \
        .pipe(f.set_default_dtypes, m=dict(group_co=bool)) \
        .rename(columns=m_cols) \
        .merge(right=df_comp, on=['Component', 'Modifier'], how='left') \
        .assign(
            Title=lambda x: x.Combined + ' - CO') \
        .drop(columns=['Component', 'Modifier', 'Combined'])

def df_ac_motor_wos():
    p = f.desktop / 'ac_motor_bands.xlsx'
    return pd.read_excel(p, sheet_name=1) \
        .pipe(f.lower_cols)

def df_srb_wos():
    p = f.desktop / 'srb_wos.csv'
    return pd.read_csv(p) \
        .pipe(f.lower_cols)

def split_wo(s):
    """Remove -seg from WO"""
    return s.str.split('-', expand=True)[0]

def find_latest_serials(df_reman, df_wo, component='AC Motor', name='ac_motor_bands', save_=False):
    """Match WOs corresponding to a component event (eg latest srb installed) to latest SNs for component from EL database

    Parameters
    ----------
    df_reman : pd.DataFrame
        df of reman's dumb access database
    df_wo : pd.DataFrame
        df of WOs to check
    component : str
        Component in EL db, default 'AC Motor'
    name : str, optional
        name to save output excel as , by default 'ac_motor_bands'
    save_ : bool, optional
        save df as excel

    Returns
    -------
    pd.DataFrame
        matched df
    
    Examples
    --------
    >>> from smseventlog.data import components as cmp
    >>> df_final = cmp.find_latest_serials(df_reman, df_srb, component='Traction Alternator', name='srb_bearing')
    """

    lst = '|'.join(df_wo.wo)
    n_chars = 10

    df2 = df_reman \
        .fillna(dict(branch_wo='', reman_wo='')) \
        .assign(
            branch_wo=lambda x: split_wo(x.branch_wo),
            reman_wo=lambda x: split_wo(x.reman_wo),
            comp_serial=lambda x: x.comp_serial.str[:n_chars]) \
        .pipe(lambda df: df[
            (df.branch_wo.str.contains(lst)) |
            (df.reman_wo.str.contains(lst))])

    # get df of most last installed SN
    query = qr.ComponentSMR()
    a = query.a

    ct = (a.MineSite=='BaseMine') | (a.MineSite=='FortHills')
    fltrs = [
        dict(ct=ct),
        dict(vals=dict(Component=component), table='ComponentType')]

    query.add_fltr_args(fltrs)
    df_comp = query.get_df()

    df_final = df_comp \
        .assign(
            last_sn=lambda x: x['Last SN Installed'].str[:n_chars],
            matches_reman=lambda x: x.last_sn.isin(f.clean_series(df2.comp_serial))) \
        .drop(columns=['Last SN Installed']) \
        .pipe(f.lower_cols)
    
    if save_:
        p = f.desktop / f'{name}.xlsx'
        df_final.to_excel(p, index=False, freeze_panes=(1, 0))

    return df_final
    
def read_comp_co_accounting():
    """Jordan's accounting excel sheet, df_acc"""
    m_cols = dict(
        ref_component_code='comp_code',
        expected_life='bench_smr',
        smr_at_change_out='unit_smr',
        smr_component_hours='comp_smr',
        work_order_number='branch_wo',
        customer_unit_number='unit',
        serial_number='serial',
        job_date_mmm_dd_yy='job_date',
        date_of_installation_mmm_dd_yy='install_date')

    p = f.desktop / 'accounting_comp_co.xlsx'
    return pd.read_excel(p, header=2, sheet_name='Transaction Input') \
        .pipe(f.default_data) \
        .rename(columns=m_cols)

def read_suncor_comp_sales():
    p = f.desktop / 'suncor_comp_sales.xlsx'
    return f.read_excel(p, header=1)
    
def merge_sun_comp_reman(df_sms, df_reman, df_acc):
    """Merge cols from sunc_comp_sales with reman wo info

    >>> df_sms = cm.read_suncor_comp_sales()
    >>> df_acc = cm.read_comp_co_accounting()
    >>> p_reman = f.desktop / '2021-03-01 - Master Product Reports_be.accdb'
    >>> df_reman = cm.load_stupid_fucking_reman_db(p=p_reman)
    """

    cols_reman = ['branch_wo', 'comp_issue']
    cols_acc = ['branch_wo', 'unit', 'install_date', 'unit_smr', 'comp_smr', 'changeout_reason'] #, 'bench_smr'

    return df_sms \
        .merge(right=df_acc[cols_acc].drop_duplicates(cols_acc), on='branch_wo', how='left') \
        .merge(right=df_reman[cols_reman].drop_duplicates(cols_reman), on='branch_wo', how='left') \
        .assign(
            unit=lambda x: x.unit.str.replace('B', ''))

def get_df_comp():
    query = qr.ComponentCO()
    a = query.a

    ct = (a.MineSite=='BaseMine') | (a.MineSite=='FortHills')
    fltrs = [
        dict(ct=ct),
        dict(vals=dict(major=1), table='ComponentType')]

    query.add_fltr_args(fltrs)
    return query.get_df() \
        .pipe(f.default_data) \
        .assign(
            branch_wo=lambda x: split_wo(x.sms_wo)
        )

def assign_has_wo(df, s_wo, col1, name):
    m = {f'has_wo_{name}': lambda x: x[col1].isin(s_wo)}

    return df \
        .assign(**m)