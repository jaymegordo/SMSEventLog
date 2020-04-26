#%% IMPORTS
import sys
from pathlib import Path
import logging
logging.basicConfig(level=logging.WARNING)

from smseventlog import *

print('**import finished')

# from PyQt5.QtCore import (QDate, QDateTime)


#%%
if False:
    import cProfile
    import pstats

    filename = 'profile_stats.stats'

    # cProfile.run('run_single(symbol=symbol,\
    # 						strattype=strattype,\
    # 						startdate=startdate,\
    # 						dfall=df,\
    # 						speed0=speed[0],\
    # 						speed1=speed[1],\
    # 						norm=norm)',
    # 						filename = filename)

    p = 'P:/Regional/SMS West Mining/SMS Event Log/Import FC/GordoJ3_200215104610_wb1.xls'
    cProfile.run('fc.read_fc(p=p)', filename=filename)
    stats = pstats.Stats(filename)
    stats.strip_dirs().sort_stats('cumulative').print_stats(30)

