import requests
from timeit import default_timer as timer
from . import functions as f
from .__init__ import *

# TODO save historical samples to db... need non-relational db



class OilSamples():
    def __init__(self, fltr=None, login=None):
        _samples = []
        
        if login is None:
            login = dict(username='jgordon', password='8\'Bigmonkeys')

        f.set_self(self, vars())

    def load_samples(self, d_lower):
        l = self.login
        startdate = d_lower.strftime('%Y-%m-%d-%H:%M:%S')
        
        url = 'https://mylab2.fluidlife.com/mylab/api/history/jsonExport?username={}&password={}&startDateTime={}'.format(l['username'], l['password'], startdate)

        start = timer()
        self._samples = requests.get(url).json()['historyList']
        print('Elapsed time: {}s'.format(f.deltasec(start, timer())))
   
    @property
    def samples(self):
        s = self._samples

        if not self.fltr is None:
            for k, v in self.fltr.items():
                s = [m for m in s if v in m[k].lower()]

        return s
    
    @property
    def samples_df(self):
        return pd.DataFrame.from_dict(self.samples) \
            .pipe(f.parse_datecols)
    
    def flagged_samples(self, fields=None, recent_only=False):
        # return flagged samples, either all or only most recent
        # check all fields, or only specified fields
        # eg: fields = ('Visc 40°C cSt', 'Visc 100°C cSt')
        df = self.samples_df

        if recent_only:
            df.sort_values(['unitId', 'componentLocation', 'sampleDate'], ascending=[True, True, False], inplace=True)
            df = df \
                .groupby(['unitId', 'componentLocation']) \
                .first() \
                .reset_index()

        df['flagged'] = df['testResults'].apply(result_flagged, fields=fields)

        return df[df.flagged==True]

def result_flagged(test_result, fields=None):
    # return true if any result is flagged
    # optional, only check specific fields

    lst = test_result
    if not fields is None:
        lst = list(filter(lambda x: any(x['testName']==field for field in fields), lst))
    
    lst_flagged = list(filter(lambda x: x['testFlag'] not in (None, ''), lst))

    return len(lst_flagged) > 0


def example():
    fltr = dict(customerName='fort hills', componentId='spindle', unitModel='980')
    oils = OilSamples(fltr=fltr)
    oils.load_samples(d_lower=dt(2020,6,1))

    return oils