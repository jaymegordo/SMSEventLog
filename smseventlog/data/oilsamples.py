import json
from timeit import default_timer as timer

import requests
from smseventlog.utils.credentials import CredentialManager

from ..queries import OilReportSpindle, OilSamples
from .__init__ import *

log = getlog(__name__)

m_names = f.config['Headers']['OilSamples']

# NOTE eventually drop records > 1yr old from db

# convert fluidlife customer_name to MineSite
m_customer = dict(
    FortHills='SUNCOR FORT HILLS ENERGY - MINE MOBILE',
    BaseMine=['SUNCOR - STEEPBANK HAUL TRUCKS', 'N.A.C.G. (SUNCOR)'],
    ConumaCoal='CONUMA COAL - WOLVERINE MINE',
    GahchoKue=['DE BEERS CANADA - GAHCHO KUE PRIMARY', "DE BEERS CANADA - GAHCHO KUE PRIMARY'"],
    Elkford='TECK COAL LTD. (ELKVIEW TRUCKS)',
    FordingRiver='TECK COAL LTD. (ELKVIEW TRUCKS)',
    GreenHills='TECK COAL LTD. (GREENHILLS)'
)

m_minesite_customer = {
    # 'carmacks': ('Carmacks', 'Carmacks'),
    'cnrl': ('CNRL', 'CNRL'),
    'copper mountain': ('CopperMountain', 'CopperMountain'),
    'diavik': ('DiavikDiamond', 'DiavikDiamond'),
    'N.A.C.G. \(SUNCOR\)': ('BaseMine', 'NACG'),
    'brule mine': ('Brule', 'Conuma Coal'),
    'willow creek': ('WillowCreek', 'Conuma Coal'),
    'wolverine': ('Wolverine', 'Conuma Coal'),
    'rainy river': ('RainyRiver', 'New Gold'),
    'steepbank': ('BaseMine', 'Suncor'),
    'fort hills': ('FortHills', 'Suncor'),
    'taseko': ('Gibraltar', 'Taseko'),
    'elkview': ('Elkford', 'ElkView'),
    'fording river': ('Elkford', 'FordingRiver'),
    'greenhills': ('Elkford', 'GreenHills'),
    'highland valley': ('HighlandValley', 'Teck')
}

class OilSamplesDownloader():
    def __init__(self, fltr=None, login=None):
        _samples = []
        _samples_full = [] # save all sample history

        if login is None:
            login = CredentialManager(name='fluidlife', gui=False).static_creds

        format_date = lambda x: x.strftime('%Y-%m-%d-00:00:00')

        f.set_self(vars())

    def build_url(self, **kw):
        l = self.login
        url = 'https://mylab2.fluidlife.com/mylab/api/history/jsonExport?'

        if not 'd_lower' in kw:
            kw['d_lower'] = dt.now() + delta(days=-14)
        
        # convert to suncor unit names
        if 'unit' in kw:
            customer = db.get_unit_val(unit=kw['unit'], field='Customer')
            if customer == 'Suncor':
                
                m = {'^F': 'F0', '^3': '03', '^2': '02'}
                for expr, repl in m.items():
                    kw['unit'] = re.sub(expr, repl, kw['unit'])

        # convert easier kws to fluidlife kws
        m_conv = dict(
            d_lower='startDateTime',
            d_upper='endDateTime',
            minesite='customerName',
            component='componentType',
            unit='unitId') # NOTE unitId doesn't actually work

        m = dict(
            username=l['username'],
            password=l['password'])
        
        kw.update(m)

        for k, v in kw.items():
            if isinstance(v, (dt)):
                v = self.format_date(v)

            # convert MineSite to Fluidlife customer_name
            if v in m_customer.keys():
                v = m_customer[v]
                if isinstance(v, list):
                    v = v[0]
            
            if k in m_conv:
                k = m_conv[k]

            ampersand = '&' if not url[-1] == '?' else ''
            url = f'{url}{ampersand}{k}={v}'
        
        return url

    def load_samples_fluidlife(self, d_lower, save_samples=False, **kw):
        """Load samples from fluidlife api, save to self._samples as list of dicts"""

        url = self.build_url(d_lower=d_lower, **kw)
        log.info(url)

        start = timer()

        new_samples = requests.get(url).json()['historyList']

        self._samples_full.extend(new_samples)
        if save_samples:
            self.save_samples()

        self._samples = new_samples

        log.info('Elapsed time: {}s'.format(f.deltasec(start, timer())))
    
    def save_samples(self):
        """Save samples to pkl file"""
        p = f.desktop / f'samples_{dt.now():%Y-%m-%d}.pkl'
        f.save_pickle(obj=self._samples_full, p=p)
        return p
        
    
    def load_samples_db(self, d_lower=None, component=None, recent=False, minesite=None, model=None):
        query = OilSamples(recent=recent, component=component, minesite=minesite, model=model)

        return query.get_df()
    
    def update_db(self):
        """Check maxdate in database, query fluidlife api, save new samples to database"""
        maxdate = db.max_date_db(table='OilSamples', field='process_date', join_minesite=False) + delta(days=-1)
        self.load_samples_fluidlife(d_lower=maxdate)
        return self.to_sql()
   
    @property
    def samples(self):
        s = self._samples

        # not sure how often this happens but samples gets returned nested 1 level deeper
        if len(s) == 1:
            s = s[0]

        if not self.fltr is None:
            for k, v in self.fltr.items():
                s = [m for m in s if v in m[k].lower()]

        return s
    
    def df_samples(self, recent=False, flatten=False):
        # only used to upload to db, otherwise use query.OilSamples()
        cols = ['hist_no', 'customer_name', 'unit_id', 'component_id', 'component_type', 'component_location', 'sample_date', 'process_date', 'meter_reading', 'component_service', 'oil_changed', 'sample_rank', 'results', 'recommendations', 'comments', 'test_results']

        # TODO need to rename all ccomponets to 

        m_rename = dict(
            unit_id='unit',
            customer_name='customer',
            meter_reading='unit_smr',
            component_service='component_smr',
            component_location='modifier')

        return pd.DataFrame.from_dict(self.samples) \
            .pipe(f.parse_datecols) \
            .pipe(f.lower_cols) \
            [cols] \
            .set_index('hist_no') \
            .rename(columns=m_rename) \
            .pipe(reduce_test_results) \
            .pipe(self.most_recent_samples, do=recent) \
            .pipe(flatten_test_results, do=flatten) \
            .pipe(db.fix_customer_units, col='unit') \
            .pipe(db.filter_database_units, col='unit') \
            .drop(columns='customer')

    
    def to_sql(self):
        """Save df to database
        - test_results is list of dicts, need to serialize
        - don't need customer in db"""

        df = self.df_samples() \
            .assign(
                test_results=lambda x: x.test_results.apply(json.dumps),
                test_flags=lambda x: x.test_flags.apply(json.dumps)) \
            .reset_index(drop=False)

        return db.insert_update(
            a='OilSamples',
            join_cols=['hist_no'],
            df=df,
            notification=True,
            import_name='OilSamples',
            chunksize=5000)
       
    def most_recent_samples(self, df, do=True):
        """NOTE not used, use query from db now"""
        if not do: return df
        return df \
            .reset_index() \
            .sort_values(
                by=['unit_id', 'component_id', 'modifier', 'sample_date'],
                ascending=[True, True, True, False]) \
            .groupby(['unit_id', 'component_id', 'modifier']) \
            .first() \
            .reset_index() \
            .set_index('hist_no')

    def flagged_samples(self, fields=None, recent=False):
        # return flagged samples, either all or only most recent
        # check all fields, or only specified fields
        # eg: fields = ('Visc 40°C cSt', 'Visc 100°C cSt')

        df = self.df_samples(recent=recent)
        df['flagged'] = df['test_results'].apply(result_flagged, fields=fields)

        return df[df.flagged==True]
    
    def df_missing_units(self):
        """Return df of all units in fluidlife sample records which aren't in the database"""
        samples = self._samples
        cols = ['unitId', 'unitSerial', 'unitModel', 'customerName']
        data = [[m[col] for col in cols] for m in samples]

        df = pd.DataFrame(data=data, columns=cols) \
            .drop_duplicates(cols) \
            .pipe(f.lower_cols) \
            .pipe(db.fix_customer_units, col='unit_id') \
            .pipe(lambda df: df[~df.unit_id.isin(db.unique_units())]) \
            .pipe(lambda df: df[df.unit_id.notna()]) \
            .sort_values(['customer_name', 'unit_id'])

        # set correct customer/minesite
        for k, (minesite, customer) in m_minesite_customer.items():
            m = dict(minesite=minesite, customer=customer)
            mask = df.customer_name.str.contains(k, case=False)

            for col in m:
                df.loc[mask, col] = m.get(col)

        return df

def result_flagged(test_result, fields=None):
    # return true if any result is flagged > apply to dataframe
    # optional, only check specific fields

    lst = test_result
    if not fields is None:
        lst = list(filter(lambda x: any(x['testName']==field for field in fields), lst))
    
    lst_flagged = list(filter(lambda x: x['testFlag'] not in (None, ''), lst))

    return len(lst_flagged) > 0

def rename_cols(df):
    return df.rename(columns=f.config['Headers']['OilSamples'])

def reduce_test_result(lst):
    """Reduce complexity/char length of test restults dicts"""
    m_res = {}
    m_flag = {}

    for m in lst:
        test = m_names.get(m['testName'], m['testName'])
        
        res = m['testResult']
        if res is None:
            res = ''
        res = f.conv_int_float_str(val=res.strip())
        m_res[test] = res

        flag = m['testFlag']
        if flag is None:
            flag = ''

        if not flag == '':
            m_flag[test] = flag

    return m_res, m_flag

def reduce_test_results(df):
    """Convert test_results to two cols of results and flags"""
    s = df.test_results.apply(reduce_test_result).tolist()
    df[['test_results', 'test_flags']] = pd.DataFrame(s, index=df.index)

    return df

def flatten_test_results(df, result_cols=None, keep_cols=None, do=True):
    # loop through list of dicts for test_results, create col with testName: testResult/testFlag for each row
    if not do: return df

    final_cols = df.columns.to_list()
    sort_order = None

    if result_cols is None: result_cols = ['testResult', 'testFlag']
    suff = dict(testResult='', testFlag='_f')

    def split_df(df, col):
        return df.loc[:, [col]] \
            .transpose() \
            .rename({col: row.Index})

    dfs_m = dd(list)
    for row in df.itertuples():
        m = row.test_results

        # get the sort order once
        if sort_order is None:
            sort_order = f.convert_list_view_db(title='OilSamples', cols=[k['testName'] for k in m])
            
        df2 = pd.DataFrame.from_dict(m) \
            .set_index('testName')

        # create a dict of lists for each result_col to use
        for result_col in result_cols:
            dfs_m[result_col].append(split_df(df=df2, col=result_col))

    for result_col in result_cols:
        df3 = pd.concat(dfs_m[result_col]) \
            .rename_axis('hist_no', axis='index') \
            .pipe(rename_cols) \
            .add_suffix(suff[result_col])
        
        # keep only specific fields, eg visc40 is in 'visc40', 'visc40_f'
        if not keep_cols is None:
            df3 = df3[[col for col in df3.columns if any(col2 in col for col2 in keep_cols)]]

        df = df.merge(df3, on='hist_no')

    # sort flattened cols, (excluding base_cols) so testResult is beside testFlag
    all_cols = df.columns.to_list()
    flattened_cols = [col for col in all_cols if not col in final_cols]
    flattened_sorted = []

    # get any cols which match current col
    for col in sort_order:
        flattened_sorted.extend([col2 for col2 in flattened_cols if col in col2])

    final_cols.extend(flattened_sorted)
    return df[final_cols]

def example():
    fltr = dict(customer_name='fort hills', component_id='spindle', unitModel='980')
    oils = OilSamplesDownloader(fltr=fltr)
    oils.load_samples_fluidlife(d_lower=dt(2020,6,1))

    return oils

def spindle_report():
    query = OilReportSpindle()
    query.add_fltr_args([
        dict(vals=dict(component='spindle'), table=query.a),
        dict(vals=dict(minesite='FortHills'), table=query.b),
        dict(vals=dict(model='980%'), table=query.b)
        ], subquery=True)

    return query.get_df()

def import_history():
    from .. import queries as qr

    oils = OilSamplesDownloader()
    rng = pd.date_range(dt(2020,1,1), dt(2021,4,1), freq='M')

    for d in rng:
        d_lower, d_upper = qr.first_last_month(d)
        d_upper = d_upper + delta(days=1)

        oils.load_samples_fluidlife(d_lower=d_lower, d_upper=d_upper, save_samples=True)
        df = oils.df_samples()
        p = f.desktop / 'fluidlife.csv'
        df.to_csv(p)
        print(f'rows downloaded from fluidlife: {df.shape}')
        oils.to_sql()
