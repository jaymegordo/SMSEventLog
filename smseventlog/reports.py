import functools

import numpy as np

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from . import functions as f
from . import queries as qr
from . import units as un
from .__init__ import *
from .database import db
from . import charts as ch

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

def set_column_style(mask, props):
    # loop columns in mask, get index, set column style
    s = []
    for i, v in enumerate(mask):
        if v == True:
            s.append(dict(
                selector=f'td:nth-child({i+1})', # css table 1-indexed not 0
                props=[props]))

    return s

def set_style(df):
    # Dataframe general column alignment/number formatting
    df.replace('\n', '<br>', inplace=True, regex=True)

    s = []
    m = f.config['color']
    s.append(dict(
        selector='th',
        props=[('text-align', 'center'), ('background', m['thead'])]))
    s.append(dict(
        selector='th, td',
        props=[('padding', '2.5px 5px')]))
    s.append(dict(
        selector='table',
        props=[('border', '1px solid #000000'), ('margin-top', '0px'), ('margin-bottom', '16px')]))

    numeric_mask = df.dtypes.apply(lambda x: issubclass(np.dtype(str(x).lower()).type, np.number))
    date_mask = df.dtypes.apply(lambda x: issubclass(np.dtype(str(x).lower()).type, np.datetime64))
    
    s.extend(set_column_style(mask=numeric_mask, props=('text-align', 'right')))
    s.extend(set_column_style(mask=~numeric_mask, props=('text-align', 'left')))
    s.extend(set_column_style(mask=date_mask, props=('text-align', 'center')))

    # Style
    style = df.style \
        .format(lambda x: '{:,.0f}'.format(x) if x > 1e3 else '{:,.2f}'.format(x), # default number format
                    subset=pd.IndexSlice[:, df.columns[numeric_mask]])\
        .set_table_styles(s) \
        .set_table_attributes('style="border-collapse: collapse"') \
        .set_na_rep('')
    
    return style

def report_unit_hrs_monthly(month):
    env = Environment(loader=FileSystemLoader(str(p_reports)))
    template = env.get_template('report_template.html')

    d = dt(dt.now().year, month, 1)
    title = 'Fort Hills Monthly SMR - {}'.format(d.strftime('%Y-%m'))
    df = un.df_unit_hrs_monthly(month=month)

    style = set_style(df)

    # specific number formats
    formats = {'int64': '{:,}', 'datetime64[ns]': '{:%Y-%m-%d}'}
    m = format_dtype(df=df, formats=formats)
    style.format(m)
    
    style.set_properties(subset=['Unit'], **{'font-weight': 'bold'})
    style.set_properties(subset=['Unit', 'Serial'], **{'text-align':'center'})

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


class Report(object):
    def __init__(self):
        # dict of {df_name: {func: func_definition, kw: **kw, df=None}}
        dfs, charts, sections = {}, {}, dd(list)
        f.set_self(self, vars())

    def get_section(self, name):
        for sec in self.sections.values():
            for item in sec:
                if item['name'] == name:
                    return item

    def add_df(self, sec, name, func=None, query=None, kw={}, display=True, has_chart=False):
        self.dfs[name] = dict(name=name, func=func, query=query, kw=kw, df=None, df_html=None, display=display, has_chart=has_chart)
        self.sections[sec].append(dict(name=name, type='df'))
    
    def add_chart(self, sec, name, func, linked=False):
        # pass name of existing df AND chart function
        self.charts[name] = dict(name=name, func=func, path='')

        # don't add to its own section if linked to display beside a df
        if not linked:
            self.sections[sec].append(dict(name=name, type='chart'))

    def load_all_dfs(self, saved=False):
        # call each df's function with its args and assign to df
        for name in self.dfs:
            self.load_df(name=name, saved=saved)

    def load_df(self, name, saved=False):
        # load df from either function defn or query obj
        m = self.dfs[name]
        func, query, kw, name = m['func'], m['query'], m['kw'], m['name']

        if saved:
            m['df'] = pd.read_csv(p_reports / f'saved/{name}.csv')
        elif not query is None:
            m['df'] = query.get_df(**kw)
        else:
            m['df'] = func(**kw)

    def print_dfs(self):
        for i, k in enumerate(self.dfs):
            m = self.dfs[k]
            rows = 0 if m['df'] is None else len(m['df'])
            val = m['query'] if not m['query'] is None else m['func']
            func = ' '.join(str(val).split(' ')[:2]).replace('<function ', '')
            print('{}: {}\n\t{}\n\t{}\n\t{}'.format(i, k, rows, func, m['kw']))
    
    def save_dfs(self):
        for m in self.dfs.values():
            df, name = m['df'], m['name']
            df.to_csv(p_reports / f'saved/{name}.csv', index=False)

    def style_df(self, name=None, df=None, query=None):
        if not name is None:
            df = self.get_df(name=name)
            query = self.get_query(name=name)

        style = set_style(df)

        # specific number formats
        formats = {'Int64': '{:,}', 'int64': '{:,}', 'datetime64[ns]': '{:%Y-%m-%d}'}
        m_fmt = format_dtype(df=df, formats=formats)

        if not query is None:
            m_fmt.update(query.formats)

            if hasattr(query, 'update_style'):
                query.update_style(style=style, df=df)

        style.format(m_fmt, na_rep='')

        return style

    def render_dfs(self):
        # convert all dataframes to html for rendering in html template
        for m in self.dfs.values():
            style = self.style_df(name=m['name'])
            m['df_html'] = style.hide_index().render()
    
    def render_charts(self):
        # render all charts from dfs, save as svg image
        for m in self.charts.values():
            df = self.dfs[m['name']]['df']
            fig = m['func'](df=df)

            p = p_reports / 'images/{}.svg'.format(m['name'])
            m['path'] = str(p)
            fig.write_image(m['path'])

    def get_all_dfs(self):
        # TODO: could probably use a filter here
        return [m['df'] for m in self.dfs.values() if not m['df'] is None]
    
    def get_df(self, name):
        return self.dfs[name]['df']

    def get_query(self, name):
        return self.dfs[name]['query']
    
    def create_pdf(self, p_base=None):
        self.render_dfs()
        self.render_charts()

        env = Environment(loader=FileSystemLoader(str(p_reports)))
        template = env.get_template('report_template.html')

        template_vars = dict(
            title=self.title,
            sections=self.sections,
            dfs=self.dfs,
            charts=self.charts)

        html_out = template.render(template_vars)
        with open('html_out.html', 'w+') as file:
            file.write(html_out)

        if p_base is None:
            p_base = Path.home() / 'Desktop'

        # save pdf
        p = p_base / f'{self.title}.pdf'
        HTML(string=html_out, base_url=str(p_reports)).write_pdf(p, stylesheets=[p_reports / 'report_style.css'])

class TestReport(Report):
    def __init__(self):
        super().__init__()
        title = 'Test Report'
        f.set_self(self, vars())

class FleetMonthlyReport(Report):
    def __init__(self, d=None, minesite='FortHills'):
        super().__init__()
        
        if d is None: d = dt.now() + delta(days=-30)
        d_rng = first_last_month(d=d)

        period = d_rng[0].strftime('%Y-%m')
        title = f'{minesite} Fleet Monthly Report - {period}'

        month = 4
        add_df, add_chart = self.add_df, self.add_chart

        sec = 'Unit SMR'
        add_df(sec=sec, name='Unit SMR', func=un.df_unit_hrs_monthly, kw=dict(month=month)) # TODO change month
        
        sec = 'Availability'
        summary = qr.AvailSummary(d_rng=d_rng)
        add_df(sec=sec, name='Summary', query=summary)

        n = 10
        name_temp = f'Top {n} Downtime Categories'
        add_df(sec=sec, name=name_temp, query=qr.AvailTopDowns(kw=dict(d_rng=d_rng, minesite=minesite, n=n)), has_chart=True)
        add_chart(sec=sec, name=name_temp, func=ch.chart_topdowns, linked=True)

        add_df(sec=sec, name='12 Month Rolling MA', query=qr.AvailRolling(d_rng=d_rng), has_chart=True)
        add_chart(sec=sec, name='12 Month Rolling MA', func=ch.chart_avail_rolling, linked=True)

        add_df(sec=sec, name='Shortfalls', query=qr.AvailShortfalls(parent=summary, kw=dict(d_rng=d_rng)))
        
        sec = 'Components'
        add_df(sec=sec, name='Component Changeout History', query=qr.ComponentCOReport(kw=dict(d_rng=d_rng, minesite=minesite)))

        sec = 'Factory Campaigns'
        add_df(sec=sec, name='New FCs', query=qr.NewFCs(d_rng=d_rng, minesite=minesite))
        add_df(sec=sec, name='Completed FCs', query=qr.FCComplete(d_rng=d_rng, minesite=minesite))

        fcsummary = qr.FCSummaryReport() # need to pass parent query to FC summary 2 to use its df
        add_df(sec=sec, name='FC Summary', query=fcsummary, kw=dict(default=True))
        add_df(sec=sec, name='FC Summary (2)', query=qr.FCSummaryReport2(parent=fcsummary))

        f.set_self(self, vars())



def first_last_month(d):
    d_lower = dt(d.year, d.month, 1)
    d_upper = d_lower + relativedelta(months=1) + delta(days=-1)
    return (d_lower, d_upper)
        


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
    # df - all components replaced in month > get component co query, filter by month
    # df - CO forecast??

# FCs
    # df - list of outstandanding mandatory FCs