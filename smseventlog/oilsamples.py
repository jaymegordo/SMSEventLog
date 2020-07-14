import json
from timeit import default_timer as timer

import requests

from . import functions as f
from . import queries as qr
from .__init__ import *
from .database import db


class OilSamples():
    def __init__(self, fltr=None, login=None):
        _samples = []
        
        if login is None:
            login = dict(username='jgordon', password='8\'Bigmonkeys')

        f.set_self(self, vars())

    def load_samples_fluidlife(self, d_lower):
        l = self.login
        startdate = d_lower.strftime('%Y-%m-%d-%H:%M:%S')
        
        url = 'https://mylab2.fluidlife.com/mylab/api/history/jsonExport?username={}&password={}&startDateTime={}'.format(l['username'], l['password'], startdate)

        start = timer()
        self._samples = requests.get(url).json()['historyList']
        print('Elapsed time: {}s'.format(f.deltasec(start, timer())))
    
    def load_samples_db(self, d_lower):
        query = qr.OilSamples()
        query.fltr.add(vals=dict(sampleDate=d_lower))
        return query.get_df()
   
    @property
    def samples(self):
        s = self._samples

        if not self.fltr is None:
            for k, v in self.fltr.items():
                s = [m for m in s if v in m[k].lower()]

        return s
    
    def df_samples(self, recent=False, flatten=False):
        cols = ['labTrackingNo', 'unitId', 'componentId', 'componentLocation', 'componentType', 'sampleDate', 'processDate', 'processNumber', 'meterReading', 'unitService', 'componentService', 'oilService', 'serviceUnits', 'oilChanged', 'sampleRank', 'results', 'recommendations', 'comments', 'testResults']

        # query lab == lab to drop None keys, (None != itself)
        df = pd.DataFrame.from_dict(self.samples)[cols] \
            .query('labTrackingNo == labTrackingNo') \
            .set_index('labTrackingNo') \
            .pipe(f.parse_datecols) \
            .pipe(self.most_recent_samples, recent) \
            .pipe(self.flatten_test_results, flatten)

        # remove suncor's leading 0s
        m = {'^F0': 'F', '^03': '3', '^02': '2'}
        df.unitId = df.unitId.replace(m, regex=True)

        # return only units which exist in the database
        df = df[df.unitId.isin(db.unique_units())]
        
        df.index = df.index.str.replace(' ', '')
        
        return df
    
    def to_sql(self):
        # save df to database
        df = self.df_samples()
        df.testResults = df.testResults.apply(json.dumps) # testResults is list of dicts, need to serialize

        return db.import_df(
            df=df, imptable='OilSamplesImport', impfunc='ImportOilSamples', notification=True, index=True, prnt=True)
    
    def flatten_test_results(self, df, do=True):
        # loop through list of dicts for testResults, create col with testName: testResult for each row
        if not do: return df

        dfs = []
        for row in df.itertuples():
            df2 = pd.DataFrame.from_dict(row.testResults) \
                .set_index('testName') \
                .drop(columns=['testType', 'testFlag']) \
                .transpose() \
                .rename(dict(testResult=row.Index))

            dfs.append(df2)

        df3 = pd.concat(dfs) \
            .rename_axis('labTrackingNo', axis='index')

        return df.merge(df3, on='labTrackingNo')
    
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
            .set_index('labTrackingNo')

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


def example():
    fltr = dict(customerName='fort hills', componentId='spindle', unitModel='980')
    oils = OilSamples(fltr=fltr)
    oils.load_samples_fluidlife(d_lower=dt(2020,6,1))

    return oils
