import pytest

from smseventlog import functions as f

def test_to_snake():

    m = {
        'WoComments': 'wo_comments',
        'SMSHelp': 'sms_help',
        'TSIHomePage': 'tsi_home_page',
        ' FC Number': 'fc_number',
        'fc number ': 'fc_number',
        'DateSMR': 'date_smr',
        ' Da\\te(SMR{': 'date_smr'}

    result = [f.to_snake(s) for s in m]
    assert result == list(m.values())
