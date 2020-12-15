import json
from timeit import default_timer as timer

import requests

from ..queries import OilReportSpindle, OilSamples
from .__init__ import *
from smseventlog.utils.credentials import CredentialManager

log = getlog(__name__)

# NOTE eventually drop records > 1yr old from db

class OilSamples():
    def __init__(self, fltr=None, login=None):
        _samples = []

        if login is None:
            login = CredentialManager(name='fluidlife', gui=False).static_creds

        f.set_self(vars())

    def load_samples_fluidlife(self, d_lower, d_upper=None):
        """Load samples from fluidlife api, save to self._samples as list of dicts"""
        l = self.login
        def _format_date(d):
            return d.strftime('%Y-%m-%d-%H:%M:%S')
        
        url = 'https://mylab2.fluidlife.com/mylab/api/history/jsonExport?username={}&password={}&startDateTime={}'.format(
            l['username'],
            l['password'],
            _format_date(d_lower))

        if not d_upper is None:
            url = f'{url}&endDateTime={_format_date(d_upper)}'

        print(url)
        start = timer()
        self._samples = requests.get(url).json()['historyList']
        print('Elapsed time: {}s'.format(f.deltasec(start, timer())))
    
    def load_samples_db(self, d_lower=None, component=None, recent=False, minesite=None, model=None):
        query = OilSamples(recent=recent, component=component, minesite=minesite, model=model)

        return query.get_df()
    
    def update_db(self):
        # check maxdate in database, query fluidlife api, save new samples to database
        maxdate = db.max_date_db(table='OilSamples', field='processDate', join_minesite=False) + delta(days=-1)
        self.load_samples_fluidlife(d_lower=maxdate)
        return self.to_sql()
   
    @property
    def samples(self):
        s = self._samples

        if not self.fltr is None:
            for k, v in self.fltr.items():
                s = [m for m in s if v in m[k].lower()]

        return s
    
    def df_samples(self, recent=False, flatten=False):
        # only used to upload to db, otherwise use query.OilSamples()
        cols = ['histNo', 'unitId', 'componentId', 'componentLocation', 'componentType', 'sampleDate', 'processDate', 'meterReading', 'componentService', 'oilChanged', 'sampleRank', 'results', 'recommendations', 'comments', 'testResults']

        # query lab == lab to drop None keys, (None != itself)
        # .query('histNo == histNo') \ # removes null/duplicates or something?
        df = pd.DataFrame.from_dict(self.samples)[cols] \
            .set_index('histNo') \
            .pipe(f.parse_datecols) \
            .pipe(self.most_recent_samples, do=recent) \
            .pipe(flatten_test_results, do=flatten)

        # remove suncor's leading 0s
        m = {'^F0': 'F', '^03': '3', '^02': '2'}
        df.unitId = df.unitId.replace(m, regex=True)

        # return only units which exist in the database
        df = df[df.unitId.isin(db.unique_units())]
        
        # df.index = df.index.str.replace(' ', '')
        
        return df
    
    def to_sql(self):
        # save df to database
        df = self.df_samples()
        df.testResults = df.testResults.apply(json.dumps) # testResults is list of dicts, need to serialize

        return db.import_df(
            df=df, imptable='OilSamplesImport', impfunc='ImportOilSamples', notification=True, index=True, prnt=True, chunksize=5000)
       
    def most_recent_samples(self, df, do=True):
        if not do: return df
        return df \
            .reset_index() \
            .sort_values(
                by=['unitId', 'componentId', 'componentLocation', 'sampleDate'],
                ascending=[True, True, True, False]) \
            .groupby(['unitId', 'componentId', 'componentLocation']) \
            .first() \
            .reset_index() \
            .set_index('histNo')

    def flagged_samples(self, fields=None, recent=False):
        # return flagged samples, either all or only most recent
        # check all fields, or only specified fields
        # eg: fields = ('Visc 40°C cSt', 'Visc 100°C cSt')

        df = self.df_samples(recent=recent)
        df['flagged'] = df['testResults'].apply(result_flagged, fields=fields)

        return df[df.flagged==True]

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

def flatten_test_results(df, result_cols=None, keep_cols=None, do=True):
    # loop through list of dicts for testResults, create col with testName: testResult/testFlag for each row
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
        m = row.testResults

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
            .rename_axis('histNo', axis='index') \
            .pipe(rename_cols) \
            .add_suffix(suff[result_col])
        
        # keep only specific fields, eg visc40 is in 'visc40', 'visc40_f'
        if not keep_cols is None:
            df3 = df3[[col for col in df3.columns if any(col2 in col for col2 in keep_cols)]]

        df = df.merge(df3, on='histNo')

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
    fltr = dict(customerName='fort hills', componentId='spindle', unitModel='980')
    oils = OilSamples(fltr=fltr)
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
