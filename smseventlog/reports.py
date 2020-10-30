import functools

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from . import charts as ch
from . import dbtransaction as dbt
from . import functions as f
from . import queries as qr
from . import styles as st
from .__init__ import *
from .data import units as un
from .database import db
from .utils import email as em
from .utils.download import Kaleido

global p_reports
p_reports = f.resources / 'reports'
log = getlog(__name__)

# TODO auto email w/ email lists

class Report(object):
    def __init__(self, d=None, d_rng=None, minesite=None, mw=None, **kw):
        # dict of {df_name: {func: func_definition, da: **da, df=None}}
        dfs, charts, sections, exec_summary, style_funcs = {}, {}, {}, {}, {}
        signatures = []
        self.html_template = 'report_template.html'
        dfs_loaded = False
        p_rep = None

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
        
        f.set_self(vars())

    def add_items(self, items : list):
        """Add report items eg Title Page, Executive Summary

        Parameters
        ----------
        items : list (or str),
            Items to add
        """        
        if not isinstance(items, list): items = [items]
        for item in items:
            self.include_items.update({item: True})

    def get_section(self, name):
        for sec in self.sections.values():
            for item in sec:
                if item['name'] == name:
                    return item

    def load_sections(self, secs : list):
        """Instantiate all sections passed in using getattr on this module.

        Parameters
        ----------
        secs : list or single items
        - str
        - dict
        """
        if not isinstance(secs, list): secs = [secs]

        for sec in secs:
            # allow passing args with dict
            if not isinstance(sec, dict):
                sec = dict(name=sec)

            getattr(sys.modules[__name__], sec['name'])(report=self, **sec)

    def load_all_dfs(self, saved=False):
        # call each df's function with its args and assign to df
        for name in self.dfs:
            self.load_df(name=name, saved=saved)
        
        self.dfs_loaded = True
        return self

    def load_df(self, name, saved=False):
        # load df from either function defn or query obj
        m = self.dfs[name]
        func, query, da, name = m['func'], m['query'], m['da'], m['name']

        if saved:
            m['df'] = pd.read_csv(p_reports / f'saved/{name}.csv')
        elif not query is None:
            m['df'] = query.get_df(**da)
        else:
            m['df'] = func(**da)

    def load_section_data(self):
        for sec in self.sections.values():
            sec.load_subsection_data()

    def print_dfs(self):
        for i, k in enumerate(self.dfs):
            m = self.dfs[k]
            rows = 0 if m['df'] is None else len(m['df'])
            val = m['query'] if not m['query'] is None else m['func']
            func = ' '.join(str(val).split(' ')[:2]).replace('<function ', '')
            print('{}: {}\n\t{}\n\t{}\n\t{}'.format(i, k, rows, func, m['da']))
    
    def save_dfs(self):
        for m in self.dfs.values():
            df, name = m['df'], m['name']
            df.to_csv(p_reports / f'saved/{name}.csv', index=False)

    def style_df(self, name=None, df=None, query=None, outlook=False, style_func=None):
        if not name is None:
            df = self.get_df(name=name)
            query = self.get_query(name=name)
            style_func = self.style_funcs.get(name, None)

        style = st.default_style(df, outlook=outlook)

        # outlook can't use css nth-child selectors, have to do manually
        if outlook:
            style = style.pipe(st.alternating_rows_outlook)

        # general number formats
        formats = {'Int64': '{:,}', 'int64': '{:,}', 'datetime64[ns]': '{:%Y-%m-%d}'}
        m_fmt = st.format_dtype(df=df, formats=formats)

        if not query is None:
            m_fmt.update(query.formats)

            if hasattr(query, 'update_style'):
                style = query.update_style(style, outlook=outlook)

        elif not style_func is None: # only needed for one df rn
            style = style_func(style)

        return style.format(m_fmt, na_rep='')

    def render_dfs(self):
        # convert all dataframes to html for rendering in html template
        for m in self.dfs.values():
            if m['display']:
                style = self.style_df(name=m['name'])
                m['df_html'] = style.hide_index().render()
    
    def check_kaleido(self):
        if SYS_FROZEN:
            if not Kaleido(mw=self.mw).check():
                return False # stop creating report
        
        return True # kaleido exists, continue creating report
    
    def render_charts(self):
        """Render all charts from dfs, save as svg image"""
        if not self.check_kaleido(): return # kaleido not installed

        # manually set executable_path for kaleido before trying to render charts
        if SYS_FROZEN:
            import kaleido.scopes.base as kaleido_base
            if f.is_win():
                kaleido_base.executable_path = f.kaleido_path
            elif f.is_mac():
                kaleido_base.BaseScope.executable_path = lambda: f.kaleido_path # need to make it a callable

        p_img = f.temp / 'images'
        if not p_img.exists():
            p_img.mkdir(parents=True)

        for m in self.charts.values():
            df = self.dfs[m['name']]['df']
            fig = m['func'](df=df, title=m['title'], **m['da'])

            p = p_img / f'{m["name"]}.svg'
            m['path'] = p # save so can delete later

            # need this to load images to html template in windows for some reason
            m['str_p_html'] = f'file:///{p.as_posix()}' if f.is_win() else str(p)

            fig.write_image(str(p), engine='kaleido')
        
        return True
    
    def remove_chart_files(self):
        """Delete images saved for charts after render."""
        for m in self.charts.values():
            p = m['path']
            try:
                p.unlink()
            except:
                log.warning(f'Couldn\'t delete image at path: {p}')

    def get_all_dfs(self):
        # TODO: could probably use a filter here
        return [m['df'] for m in self.dfs.values() if not m['df'] is None]
    
    def get_df(self, name):
        return self.dfs[name].get('df', None)

    def get_query(self, name):
        return self.dfs[name].get('query', None)
    
    def create_pdf(self, p_base=None, template_vars=None, check_overwrite=False, write_html=False, **kw):
        if not self.dfs_loaded:
            self.load_all_dfs()

        self.render_dfs()

        if self.charts:
            if not self.render_charts(): return # charts failed to render
            
        if hasattr(self, 'set_exec_summary'):
            self.set_exec_summary()

        self.load_section_data()

        template = self.env.get_template(self.html_template)

        dfs_filtered = {k:v for k, v in self.dfs.items() if v['display']} # filter out non-display dfs
        
        # can pass in extra template vars but still use originals
        if template_vars is None:
            template_vars = {}
        
        template_vars.update(dict(
                exec_summary=self.exec_summary,
                d_rng=self.d_rng,
                title=self.title,
                sections=self.sections,
                dfs=dfs_filtered,
                charts=self.charts,
                include_items=self.include_items,
                signatures=self.signatures))

        # may need to write html to file to debug issues
        html_out = template.render(template_vars)
        if write_html:
            with open('report.html', 'w+', encoding='utf-8') as file:
                file.write(html_out)

        if p_base is None:
            p_base = Path.home() / 'Desktop'

        # save pdf
        p = p_base / f'{self.title}.pdf'
        if check_overwrite and p.exists():
            from .gui.dialogs import msgbox
            msg = f'File "{p.name}" already exists. Overwrite?'
            if not msgbox(msg=msg, yesno=True):
                p = p_base / f'{self.title} (1).pdf'

        HTML(string=html_out, base_url=str(p_reports)).write_pdf(p, stylesheets=[p_reports / 'report_style.css'])

        self.remove_chart_files()
        self.p_rep = p
        return self
    
    def render_html(self, p_html, p_out=None):
        # for testing pre-created html
        if p_out is None:
            p_out = Path.home() / 'desktop/test.pdf'

        with open(p_html, 'r') as file:
            html_in = file.read()

        HTML(string=html_in, base_url=str(p_reports)).write_pdf(p_out, stylesheets=[p_reports / 'report_style.css'])

class TestReport(Report):
    def __init__(self):
        super().__init__()
        title = 'Test Report'
        self.current_period = 'April 2020'
        signatures = ['Suncor Reliability', 'Suncor Maintenance', 'SMS', 'Komatsu']

        f.set_self(vars())

        self.add_items(['signature_block'])

class FleetMonthlyReport(Report):
    def __init__(self, d=None, minesite='FortHills', secs=None, items=None):
        super().__init__(d=d)

        period_type = 'month'
        period = self.d_rng[0].strftime('%Y-%m')
        title = f'{minesite} Fleet Monthly Report - {period}'
        f.set_self(vars())
        
        if not secs:
            secs = ['UnitSMR', 'AvailBase', 'Components', 'FCs', 'FrameCracks']

        if not items:
            items = ['title_page', 'truck_logo', 'exec_summary', 'table_contents']

        self.load_sections(secs)
        self.add_items(items)
    
    @classmethod
    def example_rainyriver(cls):
        return cls(minesite='RainyRiver', secs=['FCs'], items=['title_page', 'exec_summary'])

    def set_exec_summary(self):
        gq = self.get_query
        ex = self.exec_summary
        sections = self.sections

        if 'Availability' in sections:
            self.sections['Availability'].set_exec_summary(ex=ex) # avail sets its own exec_summary
        
        if 'Components' in sections:
            ex['Components'] = gq('Component Changeout History').exec_summary()

        if 'Factory Campaigns' in sections:
            ex['Factory Campaigns'] = gq('FC Summary').exec_summary()
            ex['Factory Campaigns'].update(gq('Completed FCs').exec_summary())
    
    def email(self):
        self.set_exec_summary()
        template = self.env.get_template('exec_summary_template.html')
        template_vars = dict(
            exec_summary=self.exec_summary,
            d_rng=self.d_rng)

        html_out = template.render(template_vars) \
            .replace('Executive Summary', '')

        body = f'{f.greeting()}{html_out}'
        subject = self.title

        p = f.resources / 'csv/fleet_monthly_report_email.csv'
        email_list = list(pd.read_csv(p).Email)
        msg = em.Message(subject=subject, body=body, to_recip=email_list, show_=False)

        p = Path.home() / f'desktop/{self.title}.pdf'
        msg.add_attachment(p)
        msg.show()

class SMRReport(Report):
    def __init__(self, d=None, minesite='FortHills'):
        super().__init__(d=d)
        
        signatures = ['Suncor', 'SMS']
        period = self.d_rng[0].strftime('%Y-%m')
        title = f'{minesite} Monthly SMR - {period}'
        f.set_self(vars())

        self.load_sections('UnitSMR')
        self.add_items(['title_page', 'signature_block'])
    
    def create_pdf(self, p_base=None, csv=True):
        if csv:
            self.save_csv(p_base=p_base)

        return super().create_pdf(p_base=p_base)
    
    def save_csv(self, p_base=None):
        if p_base is None:
            p_base = Path.home() / 'Desktop'
        p = p_base / f'{self.title}.csv'
        
        df = self.get_df('SMR Hours Operated')
        df.to_csv(p)

class AvailabilityReport(Report):
    def __init__(self, d_rng, name, period_type='week', minesite='FortHills', **kw):
        super().__init__(d_rng=d_rng)

        signatures = ['Suncor Reliability', 'Suncor Maintenance', 'SMS', 'Komatsu']
            
        title = f'Suncor Reconciliation Report - {minesite} - {period_type.title()}ly - {name}'
        f.set_self(vars(), exclude='d_rng')

        self.load_sections('AvailStandalone')
        self.add_items(['title_page', 'exec_summary', 'table_contents'])

        if period_type == 'month':
            self.add_items(['signature_block'])
    
    def set_exec_summary(self):
        ex = self.exec_summary
        self.sections['Availability'].set_exec_summary(ex=ex)

class FrameCracksReport(Report):
    def __init__(self):
        super().__init__()
        self.title = 'FortHills Frame Cracks Report'
        self.load_sections('FrameCracks')
        self.add_items('title_page')

class OilSamplesReport(Report):
    def __init__(self):
        super().__init__()
        self.title = 'FortHills Spindle Oil Report'
        self.load_sections('OilSamples')
        self.add_items('title_page')

class FCReport(Report):
    def __init__(self, d=None, minesite='FortHills'):
        super().__init__(d=d)

        period_type = 'month'
        period = self.d_rng[0].strftime('%Y-%m')
        title = f'{minesite} Factory Campaign Report - {period}'
        f.set_self(vars())

        self.load_sections('FCs')

class FailureReport(Report):
    def __init__(self, title=None, header_data=None, body=None, pictures=None, e=None, ef=None, **kw):
        super().__init__()
        self.html_template = 'failure_report.html'

        # need to make image path 'absolute' with file:///
        if not pictures is None and f.is_win():
            pictures = [f'file:///{pic}' for pic in pictures]

        self.header_fields = [
            ('Failure Date', 'Work Order'),
            ('Customer', 'MineSite'),
            ('Author', None),
            ('Model', 'Part Description'),
            ('Unit', 'Part No'),
            ('Unit Serial', 'Part Serial'),
            ('Unit SMR', 'Part SMR'),
        ]
        
        # map model fields to header_data
        header_data = self.parse_header_data(m_hdr=header_data)

        if title is None:
            title = self.create_title_model(m=header_data, e=e)

        # create header table from dict of header_data
        df_head = self.df_header(m=header_data)

        # complaint/cause/correction + event work details as paragraphs with header (H4?)

        # pics > need two column layout
        f.set_self(vars())
    
    @classmethod
    def from_model(cls, e, **kw):
        """Create report from model e, with header data from event dict + unit info"""
        header_data = dbt.model_dict(e, include_none=True)
        header_data.update(db.get_df_unit().loc[e.Unit])

        return cls(e=e, header_data=header_data, **kw)

    @classmethod
    def example(cls, uid=None):
        pics = []
        e = dbt.Row.example(uid=uid)

        body = dict(
            complaint='The thing keeps breaking.',
            cause='Uncertain',
            correction='Component replaced with new.',
            details=e.Description)

        # use eventfolder to get pictures
        from . import eventfolders as efl
        ef = efl.EventFolder.example(uid=uid, e=e)
        pics = ef.pics[:3]

        return cls.from_model(e=e, ef=ef, pictures=pics, body=body)

    def create_pdf(self, p_base=None, **kw):
        if p_base is None:
            p_base = self.ef._p_event

        df_head_html = self.style_header(df=self.df_head) \
            .render()

        # convert back to caps, replace newlines
        body = {k.title(): v.replace('\n', '<br>') for k, v in self.body.items()}       

        template_vars = dict(
            df_head=df_head_html,
            body_sections=body,
            pictures=sorted(self.pictures))

        return super().create_pdf(p_base=p_base, template_vars=template_vars, check_overwrite=True, **kw)

    def style_header(self, df):
        return self.style_df(df=df) \
            .apply(st.bold_columns, subset=['field1', 'field2'], axis=None) \
            .set_table_attributes('class="failure_report_header_table"') \
            .hide_index() \
            .pipe(st.hide_headers) \

    def parse_header_data(self, m_hdr):
        m = {}
        # loop header fields, get data, else check conversion_dict
        for fields in self.header_fields:
            for field in fields:
                if not field is None:
                    m[field] = m_hdr.get(field, None) #getattr(e, field, None)

        # try again with converted headers
        m_conv = {
            'Author': 'TSIAuthor',
            'Unit SMR': 'SMR',
            'Part SMR': 'ComponentSMR',
            'Work Order': 'WorkOrder',
            'Part Description': 'TSIPartName',
            'Part No': 'PartNumber',
            'Failure Date': 'DateAdded',
            'Unit Serial': 'Serial',
            'Part Serial': 'SNRemoved',}

        for field, model_field in m_conv.items():
            m[field] = m_hdr.get(model_field, None) #getattr(e, model_field, None)

        return m

    def create_title_model(self, m=None, e=None):
        if not e is None:
            unit, d, title = e.Unit, e.DateAdded, e.Title
        elif not m is None:
            unit, d, title = m['Unit'], m['Failure Date'], '' # blank title
        else:
            return 'temp title'

        return f'{unit} - {d:%Y-%m-%d} - {title}'

    def df_header(self, m=None):
        if m is None: m = {}

        def h(val):
            return f'{val}:' if not val is None else ''

        data = [dict(
            field1=h(field1),
            field2=h(field2),
            val1=m.get(field1, None),
            val2=m.get(field2, None)) for field1, field2 in self.header_fields]

        return pd.DataFrame(data=data, columns=['field1', 'val1', 'field2', 'val2'])

class PLMUnitReport(Report):
    def __init__(self, unit : str, d_upper : dt, d_lower : dt = None, **kw):
        """Create PLM report for single unit

        Parameters
        ----------
        unit : str\n
        d_lower : dt\n
        """
        if d_lower is None:
            d_lower = qr.first_last_month(d_upper + delta(days=-180))[0]
        
        d_rng = (d_lower, d_upper)

        super().__init__(d_rng=d_rng, **kw)
        title = f'PLM Report - {unit} - {d_upper:%Y-%m-%d}'

        f.set_self(vars())

        self.load_sections('PLMUnit')

    def create_pdf(self, **kw):
        """Need to check df first to warn if no rows."""
        sec = self.sections['PLM Analysis']
        query = sec.query
        df = query.get_df()

        if df.shape[0] == 0:
            return False # cant create report with now rows

        return super().create_pdf(**kw)

class ComponentReport(Report):
    def __init__(self, d_rng, minesite, **da) -> None:
        super().__init__(d_rng=d_rng, minesite=minesite, **da)
        self.title = 'Component Changeout History - FH 980E'

        query = qr.ComponentCOReport(
            major=True,
            sort_component=True,
            da=dict(d_rng=d_rng, minesite=minesite))

        query.fltr.add(vals=dict(Model='980E*'), table=T('UnitID'))

        self.load_sections([
            dict(name='ComponentHistoryCharts', query=query),
            dict(name='Components', title='Data', query=query)])

        self.add_items(['title_page', 'exec_summary', 'table_contents'])
    
    @classmethod
    def example(cls):
        d_rng=(dt(2016,1,1), dt(2020,12,31))
        return cls(d_rng=d_rng, minesite='FortHills')

    def create_pdf(self):
        """Write raw data to csv after save"""
        super().create_pdf()
        p = self.p_rep.parent / 'FH Component Changeout History.csv'
        df = self.get_df('Component Changeout History')
        df.to_csv(p, index=False)

        return self

    def set_exec_summary(self):
        gq = self.get_query
        ex = self.exec_summary       
        ex['Components'] = gq('Component Changeout History').exec_summary()


# REPORT SECTIONS
class Section():
    # sections only add subsections
    def __init__(self, title, report, **kw):
        
        report.sections[title] = self # add self to parent report
        sub_sections = {}
        d_rng, d_rng_ytd, minesite = report.d_rng, report.d_rng_ytd, report.minesite

        f.set_self(vars())
    
    def add_subsections(self, sections):
        for name in sections:
            subsec = getattr(sys.modules[__name__], name)(section=self)
    
    def load_subsection_data(self):
        """Load extra data (eg paragraph data) for each subsection"""
        for name, sub_sec in self.sub_sections.items():
            if not sub_sec.paragraph_func is None:
                m = sub_sec.paragraph_func
                sub_sec.paragraph = m['func'](**m['kw'])

class OilSamples(Section):
    def __init__(self, report, **kw):
        super().__init__(title='Oil Samples', report=report)

        sec = SubSection('Spindles', self) \
            .add_df(
                query=qr.OilReportSpindle(),
                da=dict(default=True),
                caption='Most recent spindle oil samples.')

class FrameCracks(Section):
    def __init__(self, report, **kw):
        super().__init__(title='Frame Cracks', report=report)
        from .data import framecracks as frm

        m = dict(df=frm.load_processed_excel())
        
        sec = SubSection('Summary', self) \
            .add_df(
                func=frm.df_smr_avg,
                da=m,
                caption='Mean SMR cracks found at specified loaction on haul truck.<br><br>Rear = rear to mid torque tube<br>Mid = mid torque tube (inclusive) to horse collar<br>Front = horse collar (inclusive) to front.')

        sec = SubSection('Frame Cracks Distribution', self) \
            .add_df(
                name='Frame Cracks (Monthly)',
                func=frm.df_month,
                da=m,
                display=False) \
            .add_df(
                name='Frame Cracks (SMR Range)',
                func=frm.df_smr_bin,
                da=m,
                display=False) \
            .add_chart(
                name='Frame Cracks (Monthly)',
                func=ch.chart_frame_cracks,
                caption='Frame crack type distributed by month.') \
            .add_chart(
                name='Frame Cracks (SMR Range)',
                func=ch.chart_frame_cracks,
                caption='Frame crack type distributed by Unit SMR.',
                da=dict(smr_bin=True)) \
            .force_pb = True

class UnitSMR(Section):
    def __init__(self, report, **kw):
        super().__init__(title='SMR Hours', report=report)

        d = report.d_rng[0]
        month = d.month
        sec = SubSection('SMR Hours Operated', self) \
            .add_df(
                func=un.df_unit_hrs_monthly,
                da=dict(month=month),
                caption='SMR hours operated during the report period.') # TODO change month, make query

class AvailBase(Section):
    def __init__(self, report, **kw):
        super().__init__(title='Availability', report=report)

        n = 10
        d_rng, d_rng_ytd, ms, period_type = self.d_rng, self.d_rng_ytd, self.minesite, self.report.period_type

        summary = qr.AvailSummary(d_rng=d_rng)
        summary_ytd = qr.AvailSummary(d_rng=d_rng_ytd)
        sec = SubSection('Fleet Availability', self) \
            .add_df(
                query=summary,
                caption='Unit availability performance vs MA targets. Units highlighted blue met the target. Columns [Total, SMS, Suncor] highlighted darker red = worse performance.<br>*Unit F300 excluded from summary calculations.') \
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
                query=qr.AvailTopDowns(da=dict(d_rng=d_rng, minesite=ms, n=n)), 
                has_chart=True,
                caption=f'Top {n} downtime categories (report period).') \
            .add_chart(
                name=name_topdowns,
                func=ch.chart_topdowns, 
                linked=True) \
            .add_df(
                name=name_topdowns_ytd, 
                query=qr.AvailTopDowns(da=dict(d_rng=d_rng_ytd, minesite=ms, n=n)), 
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
                da=dict(period_type=period_type))
        sec.force_pb = True

        sec = SubSection('MA Shortfalls', self) \
            .add_df(
                query=qr.AvailShortfalls(parent=summary, da=dict(d_rng=d_rng)),
                caption='Detailed description of major downtime events (>12 hrs) for units which did not meet MA target.')
        
        f.set_self(vars())
    
    def set_exec_summary(self, ex):
        gq, m = self.report.get_query, {}
        
        m.update(gq('Fleet Availability').exec_summary())
        m.update(gq('Fleet Availability YTD').exec_summary())
        m.update(gq(self.name_topdowns).exec_summary())

        ex['Availability'] = m

class AvailStandalone(AvailBase):
    def __init__(self, report, **kw):
        super().__init__(report)

        sec = SubSection('Raw Data', self) \
            .add_df(
                query=qr.AvailRawData(da=dict(d_rng=self.d_rng)),
                caption='Raw downtime data for report period.')

class Components(Section):
    def __init__(self, report, title='Components', query=None, **kw):
        """Table of component changeout records"""
        super().__init__(title=title, report=report)
        sec_name = 'Component Changeout History'

        if query is None:
            query = qr.ComponentCOReport(da=dict(d_rng=self.d_rng, minesite=self.minesite))

        sec = SubSection(sec_name, self) \
            .add_df(
                query=query,
                caption='Major component changeout history. Life achieved is the variance between benchmark SMR and SMR at changeout.')
        
        f.set_self(vars())
        
class ComponentHistoryCharts(Section):
    def __init__(self, report, query, **kw):
        """Charts showing breakdown of component changeouts by type, quarterly and by """
        super().__init__(title='Summary', report=report)

        sec = SubSection('Mean Life', self) \
            .add_df(
                func=query.df_mean_life,
                style_func=query.update_style_mean_life,
                caption='Mean SMR at component changeout.<br><br>Notes:<br>\
                    - Bench_Pct_All is the mean SMR of all changeouts compared to the group\'s benchmark SMR.<br>\
                    - This table only includes "Failure/Warranty" and "High Hour Changeout" values.')

        sec = SubSection('Component Changeouts (Quarterly)', self) \
            .add_df(
                func=query.df_component_quarter,
                has_chart=True,
                display=False) \
            .add_chart(
                func=ch.chart_comp_co,
                cap_align='left',
                caption='Component changeout type grouped per quarter.')
        sec.force_pb = True
            
        sec = SubSection('Component Failure Rates', self) \
            .add_df(
                func=query.df_failures,
                has_chart=True,
                display=False) \
            .add_chart(
                func=ch.chart_comp_failure_rates,
                cap_align='left',
                caption='Component failure rates by category.<br>Failed = [Failed, Warranty]<br>Not Failed = [Convenience, High Hour Changeout, Damage/Abuse, Pro Rata Buy-in, Other]')

class PLMUnit(Section):
    def __init__(self, report, **kw):
        super().__init__(title='PLM Analysis', report=report)
        d_rng = report.d_rng
        unit = report.unit

        self.query = qr.PLMUnit(
            unit=unit, d_lower=d_rng[0], d_upper=d_rng[1])
        query = self.query

        sec = SubSection('Summary', self) \
            .add_df(
                func=query.df_summary_report,
                style_func=query.update_style,
                caption=f'PLM Summary for unit {unit}') \
            .add_paragraph(
                func=self.set_paragraph,
                kw=dict(query=query))
        
        sec = SubSection('Payload History', self) \
            .add_df(
                func=query.df_monthly,
                has_chart=True,
                display=False) \
            .add_chart(
                func=ch.chart_plm_monthly,
                cap_align='left',
                caption='PLM haul records per month.<br>*Note - final month may not represent complete month.')
           
    def set_paragraph(self, query, **kw):
        """Set paragraph data from query
        - NOTE query needs to already be loaded, must call after load_dfs
        """

        # if not hasattr(query, 'df_orig'):
        #     raise AttributeError('Query df not loaded yet!')

        m = query.df_summary.iloc[0].to_dict()

        header = {
            'Unit': m['Unit'],
            'MinDate': f"{m['MinDate']:%Y-%m-%d}",
            'MaxDate': f"{m['MaxDate']:%Y-%m-%d}",
            'Total Loads': f"{m['TotalLoads']:,.0f}",
            'Accepted Loads': f"{m['Total_ExcludeFlags']:,.0f}"
        }

        return f.two_col_list(header)

class FCs(Section):
    def __init__(self, report, **kw):
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
                query=qr.NewFCs(d_rng=d_rng, minesite=minesite),
                caption='All new FCs released during the report period.')
        
        sec = SubSection('Completed FCs', self) \
            .add_df(
                query=qr.FCComplete(d_rng=d_rng, minesite=minesite),
                caption='FCs completed during the report period.')

        fcsummary = qr.FCSummaryReport(minesite=minesite) # need to pass parent query to FC summary 2 to use its df
        sec = SubSection('FC Summary', self) \
            .add_df(
                query=fcsummary,
                da=dict(default=True),
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
        paragraph = None
        paragraph_func = None
        force_pb = False
        f.set_self(vars())

    def add_df(self, name=None, func=None, query=None, da={}, display=True, has_chart=False, caption=None, style_func=None):
        if name is None:
            name = self.title

        self.report.dfs[name] = dict(
            name=name,
            func=func,
            query=query,
            da=da,
            df=None,
            df_html=None,
            display=display,
            has_chart=has_chart)

        self.report.style_funcs.update({name: style_func})

        if display:
            self.elements.append(dict(name=name, type='df', caption=caption))
        
        return self
    
    def add_chart(self, func, name=None, linked=False, title=None, caption=None, da={}, cap_align='center'):
        if name is None:
            name = self.title
        
        # pass name of existing df AND chart function
        self.report.charts[name] = dict(name=name, func=func, path='', title=title, da=da)

        # don't add to its own section if linked to display beside a df
        if not linked:
            cap_class = f'figcaption_{cap_align}' # align chart caption left or center
            self.elements.append(dict(name=name, type='chart', caption=caption, cap_class=cap_class))
        
        return self
    
    def add_paragraph(self, func, kw=None):
        if kw is None: kw = {}

        self.paragraph_func = dict(func=func, kw=kw)
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
