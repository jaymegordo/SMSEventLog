import functools

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from . import charts as ch
from . import email as em
from . import functions as f
from . import queries as qr
from . import styles as st
from . import units as un
from .__init__ import *
from .database import db

global p_reports
p_reports = f.datafolder / 'reports'

# TODO auto email w/ email lists

class Report(object):
    def __init__(self, d=None, d_rng=None, minesite=None, **kw):
        # dict of {df_name: {func: func_definition, kw: **kw, df=None}}
        dfs, charts, sections, exec_summary, style_funcs = {}, {}, {}, {}, {}

        if d is None: d = dt.now() + delta(days=-31)
        if d_rng is None: d_rng = qr.first_last_month(d=d)

        # make sure everything is date not datetime
        if isinstance(d_rng[0], dt):
            d_rng = (d_rng[0].date(), d_rng[1].date())
            
        d_rng_ytd = (dt(dt.now().year, 1, 1).date(), d_rng[1])

        include_items = dict(
            title_page=False,
            truck_logo=False,
            exec_summary=False,
            table_contents=False,
            signature_block=False)
        
        env = Environment(loader=FileSystemLoader(str(p_reports)))
        
        f.set_self(self, vars())

    def add_items(self, items):
        if not isinstance(items, list): items = [items]
        for item in items:
            self.include_items.update({item: True})

    def get_section(self, name):
        for sec in self.sections.values():
            for item in sec:
                if item['name'] == name:
                    return item

    def load_sections(self, secs):
        if not isinstance(secs, list): secs = [secs]
        for sec_name in secs:
            getattr(sys.modules[__name__], sec_name)(report=self)

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

    def style_df(self, name=None, df=None, query=None, outlook=False):
        if not name is None:
            df = self.get_df(name=name)
            query = self.get_query(name=name)
            style_func = self.style_funcs.get(name, None)

        style = st.set_style(df)

        # outlook can't use css nth-child selectors, have to do manually
        if outlook:
            style = style.pipe(st.alternating_rows_outlook)

        # general number formats
        formats = {'Int64': '{:,}', 'int64': '{:,}', 'datetime64[ns]': '{:%Y-%m-%d}'}
        m_fmt = st.format_dtype(df=df, formats=formats)

        if not query is None:
            m_fmt.update(query.formats)

            if hasattr(query, 'update_style'):
                style = query.update_style(style)

        elif not style_func is None: # only needed for one df rn
            style = style_func(style)

        style.format(m_fmt, na_rep='')

        return style

    def render_dfs(self):
        # convert all dataframes to html for rendering in html template
        for m in self.dfs.values():
            if m['display']:
                style = self.style_df(name=m['name'])
                m['df_html'] = style.hide_index().render()
    
    def render_charts(self):
        # render all charts from dfs, save as svg image
        if f.frozen:
            # TODO user has to install orca manually, need to check and give instructions
            # have to specify absolute path to orca for exporting plotly charts as images
            import plotly.io.orca as orca
            if not f.is_win():
                orca_path = '/Applications/orca.app/Contents/MacOS/orca' 
            else:
                # TODO figure out this path for windows
                orca_path = '/path/to/pyinstalled/orca/orca.exe'
                
            orca.config.executable = orca_path
            orca.config._constants['plotlyjs']  = str(f.topfolder / 'plotly/package_data/plotly.min.js')

        for m in self.charts.values():
            df = self.dfs[m['name']]['df']
            fig = m['func'](df=df, title=m['title'], **m['kw'])

            p = p_reports / 'images/{}.svg'.format(m['name'])
            m['path'] = str(p)
            fig.write_image(m['path'])

    def get_all_dfs(self):
        # TODO: could probably use a filter here
        return [m['df'] for m in self.dfs.values() if not m['df'] is None]
    
    def get_df(self, name):
        return self.dfs[name].get('df', None)

    def get_query(self, name):
        return self.dfs[name].get('query', None)
    
    def create_pdf(self, p_base=None):
        self.render_dfs()
        self.render_charts()
        if hasattr(self, 'set_exec_summary'):
            self.set_exec_summary()

        template = self.env.get_template('report_template.html')

        dfs_filtered = {k:v for k, v in self.dfs.items() if v['display']} # filter out non-display dfs
        print(self.d_rng)
        template_vars = dict(
            exec_summary=self.exec_summary,
            d_rng=self.d_rng,
            title=self.title,
            sections=self.sections,
            dfs=dfs_filtered,
            charts=self.charts,
            include_items=self.include_items)

        html_out = template.render(template_vars)
        with open('html_out.html', 'w+', encoding='utf-8') as file:
            file.write(html_out)

        if p_base is None:
            p_base = Path.home() / 'Desktop'

        # save pdf
        p = p_base / f'{self.title}.pdf'
        HTML(string=html_out, base_url=str(p_reports)).write_pdf(p, stylesheets=[p_reports / 'report_style.css'])

        return p

class TestReport(Report):
    def __init__(self):
        super().__init__()
        title = 'Test Report'
        self.current_period = 'April 2020'

        ex = self.exec_summary
        ex['Availability'] =  {
            self.current_period: {
                'Physical Availability': '69.0%',
                'Mechanical Availability': '90.0%',
                'Target MA': '92.0%'
            },
            'YTD': {
                'Physical Availability': '69.0%',
                'Mechanical Availability': '90.0%',
                'Target MA': '92.0%'
            },
            'Top 3 downtime categories': {
                'Engine': '30%',
                'S4 Service': '22%',
                'S5 Service': '21%'
            }
        }

        ex['Components'] = {
            'Changeouts': {
                'Planned': 26,
                'Break-in': 11}}

        ex['Factory Campaigns'] = {
            'Outstanding': {
                'M': 44,
                'FAF/FT': 13,
                'Labour Hours': 1234
            },
            'Completed': {
                'M': 13,
                'FAF/FT': 3,
                'Labour Hours': 123
            }
        }
        f.set_self(self, vars())

class FleetMonthlyReport(Report):
    def __init__(self, d=None, minesite='FortHills'):
        super().__init__(d=d)

        period_type = 'month'
        period = self.d_rng[0].strftime('%Y-%m')
        title = f'{minesite} Fleet Monthly Report - {period}'
        f.set_self(self, vars())

        secs = ['UnitSMR', 'Availability', 'Components', 'FCs', 'FrameCracks']
        self.load_sections(secs)
        self.add_items(['title_page', 'truck_logo', 'exec_summary', 'table_contents'])

    def set_exec_summary(self):
        gq = self.get_query
        ex = self.exec_summary

        self.sections['Availability'].set_exec_summary(ex=ex) # avail sets its own exec_summary
        
        ex['Components'] = gq('Component Changeout History').exec_summary()

        ex['Factory Campaigns'] = gq('FC Summary').exec_summary()
        ex['Factory Campaigns'].update(gq('Completed FCs').exec_summary())
    
    def email(self):
        self.set_exec_summary()
        template = self.env.get_template('exec_summary_template.html')
        template_vars = dict(
            exec_summary=self.exec_summary,
            d_rng=self.d_rng)

        html_out = template.render(template_vars)
        body = f'{f.greeting()}{html_out}'
        subject = self.title

        p = f.datafolder / 'csv/fleet_monthly_report_email.csv'
        email_list = list(pd.read_csv(p).Email)
        msg = em.Message(subject=subject, body=body, to_recip=email_list, show_=False)

        p = Path.home() / f'desktop/{self.title}.pdf'
        msg.add_attachment(p)
        msg.show()

class MonthlySMRReport(Report):
    def __init__(self, d=None, minesite='FortHills'):
        super().__init__(d=d)
        
        period = self.d_rng[0].strftime('%Y-%m')
        title = f'{minesite} Monthly SMR - {period}'
        f.set_self(self, vars())

        self.load_sections('UnitSMR')
        self.add_items(['title_page', 'signature_block'])
    
    def create_pdf(self, p_base=None, csv=False):
        super().create_pdf(p_base=p_base)
        if csv:
            self.save_csv()
    
    def save_csv(self):
        p_base = Path.home() / 'Desktop'
        p = p_base / f'{self.title}.csv'
        
        df = self.get_df('SMR Hours Operated')
        df.to_csv(p)

class AvailabilityReport(Report):
    def __init__(self, d_rng, name, period_type='week', minesite='FortHills'):
        super().__init__(d_rng=d_rng)

        # get correct weekly or monthly date range
            
        title = f'Suncor Reconciliation Report - {minesite} - {period_type.title()}ly - {name}'
        f.set_self(self, vars(), exclude='d_rng')

        self.load_sections('AvailReport')
        self.add_items(['title_page', 'exec_summary', 'table_contents'])
    
    def set_exec_summary(self):
        ex = self.exec_summary
        self.sections['Availability'].set_exec_summary(ex=ex)

class FrameCracksReport(Report):
    def __init__(self):
        super().__init__()
        self.title = 'FortHills Frame Cracks Report'
        self.load_sections('FrameCracks')
        self.add_items('title_page')
    

# REPORT SECTIONS
class Section():
    # sections only add subsections
    def __init__(self, title, report):
        
        report.sections[title] = self # add self to parent report
        sub_sections = {}
        d_rng, d_rng_ytd, minesite = report.d_rng, report.d_rng_ytd, report.minesite

        f.set_self(self, vars())
    
    def add_subsections(self, sections):
        for name in sections:
            subsec = getattr(sys.modules[__name__], name)(section=self)

class FrameCracks(Section):
    def __init__(self, report):
        super().__init__(title='Frame Cracks', report=report)
        from . import framecracks as frm

        m = dict(df=frm.load_processed_excel())
        
        sec = SubSection('Summary', self) \
            .add_df(
                func=frm.df_smr_avg,
                kw=m,
                caption='Mean SMR cracks found at specified loaction on haul truck.<br><br>Rear = rear to mid torque tube<br>Mid = mid torque tube (inclusive) to horse collar<br>Front = horse collar (inclusive) to front.')

        sec = SubSection('Frame Cracks Distribution', self) \
            .add_df(
                name='Frame Cracks (Monthly)',
                func=frm.df_month,
                kw=m,
                display=False) \
            .add_df(
                name='Frame Cracks (SMR Range)',
                func=frm.df_smr_bin,
                kw=m,
                display=False) \
            .add_chart(
                name='Frame Cracks (Monthly)',
                func=ch.chart_frame_cracks,
                caption='Frame crack type distributed by month.') \
            .add_chart(
                name='Frame Cracks (SMR Range)',
                func=ch.chart_frame_cracks,
                caption='Frame crack type distributed by Unit SMR.',
                kw=dict(smr_bin=True)) \
            .force_pb = True

class UnitSMR(Section):
    def __init__(self, report):
        super().__init__(title='SMR Hours', report=report)

        d = report.d_rng[0]
        month = d.month
        sec = SubSection('SMR Hours Operated', self) \
            .add_df(
                func=un.df_unit_hrs_monthly,
                kw=dict(month=month),
                caption='SMR hours operated during the report period.') # TODO change month, make query

class Availability(Section):
    def __init__(self, report):
        super().__init__(title='Availability', report=report)

        n = 10
        d_rng, d_rng_ytd, ms, period_type = self.d_rng, self.d_rng_ytd, self.minesite, self.report.period_type

        summary = qr.AvailSummary(d_rng=d_rng)
        summary_ytd = qr.AvailSummary(d_rng=d_rng_ytd)
        sec = SubSection('Fleet Availability', self) \
            .add_df(
                query=summary,
                caption='Unit availability performance vs MA targets. Units highlighted blue met the target. Columns [Total, SMS, Suncor] highlighted darker red = worse performance.') \
            .add_df(
                name='Fleet Availability YTD', 
                query=summary_ytd, 
                display=False) \
            .add_df(
                name='Summary Totals',
                caption='Totals for units in Staffed vs AHS operation.',
                func=summary.df_totals,
                style_func=summary.style_totals) \
            .add_chart(
                func=ch.chart_fleet_ma,
                caption='Unit mechanical availabilty performance vs MA target (report period).') \
            .add_chart(
                name='Fleet Availability YTD',
                func=ch.chart_fleet_ma,
                title='Fleet MA - Actual vs Target (YTD)',
                caption='Unit mechanical availabilty performance vs MA target (YTD period).')


        title_topdowns = f'Downtime Categories'
        name_topdowns = f'Top {n} {title_topdowns}'
        name_topdowns_ytd = f'{name_topdowns} (YTD)'

        sec = SubSection(title_topdowns, self) \
            .add_df(
                name=name_topdowns,
                query=qr.AvailTopDowns(kw=dict(d_rng=d_rng, minesite=ms, n=n)), 
                has_chart=True,
                caption=f'Top {n} downtime categories (report period).') \
            .add_chart(
                name=name_topdowns,
                func=ch.chart_topdowns, 
                linked=True) \
            .add_df(
                name=name_topdowns_ytd, 
                query=qr.AvailTopDowns(kw=dict(d_rng=d_rng_ytd, minesite=ms, n=n)), 
                has_chart=True,
                caption=f'Top {n} downtime categories (YTD period).') \
            .add_chart(
                name=name_topdowns_ytd, 
                func=ch.chart_topdowns,
                title=name_topdowns_ytd, 
                linked=True)

        # needs to be subsec so can be weekly/monthly
        sec = SubSection('Availability History', self) \
            .add_df(
                query=qr.AvailHistory(d_rng=d_rng, period_type=period_type), 
                has_chart=False,
                caption=f'12 {period_type} rolling availability performance vs targets.') \
            .add_chart(
                func=ch.chart_avail_rolling,
                linked=False,
                caption=f'12 {period_type} rolling availability vs downtime hours.',
                kw=dict(period_type=period_type))
        sec.force_pb = True

        sec = SubSection('MA Shortfalls', self) \
            .add_df(
                query=qr.AvailShortfalls(parent=summary, kw=dict(d_rng=d_rng)),
                caption='Detailed description of major downtime events (>12 hrs) for units which did not meet MA target.')
        
        f.set_self(self, vars())
    
    def set_exec_summary(self, ex):
        gq, m = self.report.get_query, {}
        
        m.update(gq('Fleet Availability').exec_summary())
        m.update(gq('Fleet Availability YTD').exec_summary())
        m.update(gq(self.name_topdowns).exec_summary())

        ex['Availability'] = m

class AvailReport(Availability):
    def __init__(self, report):
        super().__init__(report)

        sec = SubSection('Raw Data', self) \
            .add_df(
                query=qr.AvailRawData(kw=dict(d_rng=self.d_rng)),
                caption='Raw downtime data for report period.')

class Components(Section):
    def __init__(self, report):
        super().__init__(title='Components', report=report)

        sec = SubSection('Component Changeout History', self) \
            .add_df(
                query=qr.ComponentCOReport(kw=dict(d_rng=self.d_rng, minesite=self.minesite)),
                caption='Major component changeout history. Life achieved is the variance between benchmark SMR and SMR at changeout.')

class FCs(Section):
    def __init__(self, report):
        super().__init__(title='Factory Campaigns', report=report)
        d_rng, minesite = self.d_rng, self.minesite

        sec = SubSection('Outstanding FCs', self) \
            .add_df(
                query=qr.FCHistoryRolling(d_rng=d_rng, minesite=minesite),
                display=False) \
            .add_chart(
                func=ch.chart_fc_history,
                linked=False,
                caption='Outstanding mandatory FCs vs labour hours. (Measured at end of month).')

        sec = SubSection('New FCs', self) \
            .add_df(
                name='New FCs',
                query=qr.NewFCs(d_rng=d_rng, minesite=minesite),
                caption='All new FCs released during the report period.')
        
        print(minesite)
        sec = SubSection('Completed FCs', self) \
            .add_df(
                query=qr.FCComplete(d_rng=d_rng, minesite=minesite),
                caption='FCs completed during the report period.')

        fcsummary = qr.FCSummaryReport() # need to pass parent query to FC summary 2 to use its df
        sec = SubSection('FC Summary', self) \
            .add_df(
                query=fcsummary, kw=dict(default=True),
                caption='Completion status of currently open FCs.') \
            .add_df(
                name='FC Summary (2)',
                query=qr.FCSummaryReport2(parent=fcsummary),
                caption='Completion status of FCs per unit. (Extension of previous table, mandatory FCs highlighted navy blue).')

class SubSection():
    # subsections add dfs/charts/paragraphs
    def __init__(self, title, section):
        
        section.sub_sections[title] = self # add self to parent's section
        report = section.report
        elements = []
        force_pb = False
        f.set_self(self, vars())

    def add_df(self, name=None, func=None, query=None, kw={}, display=True, has_chart=False, caption=None, style_func=None):
        if name is None:
            name = self.title

        self.report.dfs[name] = dict(name=name, func=func, query=query, kw=kw, df=None, df_html=None, display=display, has_chart=has_chart)

        self.report.style_funcs.update({name: style_func})

        if display:
            self.elements.append(dict(name=name, type='df', caption=caption))
        
        return self
    
    def add_chart(self, func, name=None, linked=False, title=None, caption=None, kw={}):
        if name is None:
            name = self.title
        
        # pass name of existing df AND chart function
        self.report.charts[name] = dict(name=name, func=func, path='', title=title, kw=kw)

        # don't add to its own section if linked to display beside a df
        if not linked:
            self.elements.append(dict(name=name, type='chart', caption=caption))
        
        return self




        

# TSI
    # number of TSIs submitted per month?

# Fault codes
    # need to bulk import all faults

# PLM
    # Will need to manually import all units before running report for now. > wont have dls till much later..
    # df - summary table - total loads, total payload, fleet mean payload
    # chart - monthly rolling summary
    # df - summary loads per unit, need to identify max payload date..

# Component CO
    # df - CO forecast??
