import functools

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from . import functions as f
from . import units as un
from .__init__ import *

global p_reports
p_reports = Path(__file__).parents[1] / 'reports'

# Dataframe format
def left_justified(df, header=False):
    formatters = {}
    for li in list(df.columns):
        max = df[li].str.len().max()
        form = "{{:<{}s}}".format(max)
        formatters[li] = functools.partial(str.format, form)
    # display(formatters)
    return df.to_string(formatters=formatters, index=False, header=header)

def format_dtype(df, formats):
    # match formats to df.dtypes
    # formats = {'int64': '{:,}'}
    # df.dtypes = {'Unit': dtype('O'),
                # datetime.dt(2020, 3, 1): dtype('int64'),
    m = {}
    for key, fmt in formats.items():
        m.update({col: fmt for col, val in df.dtypes.to_dict().items() if val==key})
    
    return m

def set_style(df):
    # Dataframe general column alignment/number formatting
    # Mask of numeric columns
    numeric_col_mask = df.dtypes.apply(lambda x: issubclass(np.dtype(x).type, np.number))

    # Center table headers
    d = dict(
        selector='th',
        props=[('text-align', 'center')])

    # Style
    style = df.style \
        .set_properties(subset=df.columns[numeric_col_mask], **{'text-align':'right'})\
        .set_properties(subset=df.columns[~numeric_col_mask], **{'text-align':'center'})\
        .format(lambda x: '{:,.0f}'.format(x) if x > 1e3 else '{:,.2f}'.format(x), # format numeric values
                    subset=pd.IndexSlice[:, df.columns[numeric_col_mask]])\
        .set_table_styles([d])
    
    return style

def report_unit_hrs_monthly(month):

    env = Environment(loader=FileSystemLoader(str(p_reports)))
    template = env.get_template('report_template.html')

    d = dt(dt.now().year, month, 1)
    title = 'Fort Hills Monthly SMR - {}'.format(dt.strftime('%Y-%m'))
    df = un.df_unit_hrs_monthly(month=month)

    style = set_style(df)

    formats = dict(int64='{:,}')
    m = format_dtype(df=df, formats=formats)
    style.format(m)
    
    style.set_properties(subset=['Unit'], **{'font-weight': 'bold'})

    html_tbl = style.hide_index().render()
    template_vars = {'title' : title,
                 'unit_hrs': html_tbl}
    html_out = template.render(template_vars)

    p_base = Path.home() / 'Desktop'

    # save pdf
    p = p_base / f'{title}.pdf'
    HTML(string=html_out).write_pdf(p, stylesheets=[p_reports / 'report_style.css'])

    # save csv
    p = p_base / f'{title}.csv'
    df.to_csv(p)

def get_df():
    # get raw df

    # process/shape?

    # style

    # set col formats
    
    return

# Fleet Monthly Report
def fleet_monthly_report(month):

    # create template
        # table of contents?

    # get all dfs

    # SMR hrs - done
    df_smr = un.df_unit_hrs_monthly(month=month)

    # Availability
        # df - Monthly avail summary > get from db - done
        # chart - rolling availability > create from df, exists in db?
        # df - MA shortfalls > maybe need to create this?
        # df - year to date? maybe just df of monthly rolling?
        # chart/df - top x downtime reasons

    # PLM
        # Will need to manually import all units before running report for now. > wont have dls till much later..
        # df - summary table - total loads, total payload, fleet mean payload
        # chart - monthly rolling summary
        # df - summary loads per unit, need to identify max payload date..
    
    # Component CO
        # df - all components replaced in month
        # df - CO forecast??

    # FCs
        # df - New FCs released
        # df - Full summary page
        # df - FCs completed during the month summary per fc/count
        # df - list of outstandanding mandatory FCs


    # match df.html to template slots

    # save as pdf
    
    return