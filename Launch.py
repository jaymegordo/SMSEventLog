#%% IMPORTS
if True:
	import cProfile
	import json
	import os
	import sys
	from datetime import datetime as date
	from datetime import timedelta as delta
	from pathlib import Path
	from time import time
	from timeit import Timer

	import pandas as pd
	import xlwings as xw
	import yaml
	import pypika as pk

	import eventlog as el
	import folders as fl
	import factorycampaign as fc
	import functions as f
	import userforms as uf
	from database import db

# %%
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

