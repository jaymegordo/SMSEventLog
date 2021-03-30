import numpy as np

from . import functions as f
from .__init__ import *


# Dataframe format
def left_justified(df, header=False):
    formatters = {}
    for li in list(df.columns):
        max_ = df[li].str.len().max()
        form = '{{:<{}s}}'.format(max_)
        formatters[li] = partial(str.format, form)
    # display(formatters)
    return df.to_string(formatters=formatters, index=False, header=header)

def format_dtype(df, formats):
    """Match formats to df.dtypes
    - format can be either string or func
    - formats = {'int64': '{:,}'}
    - df.dtypes = {'Unit': dtype('O'),
                datetime.dt(2020, 3, 1): dtype('int64'),"""
    m = {}
    for key, fmt in formats.items():
        # need str(val) to convert np dtype to string to avoid failed comparisons to pd.Int64 etc
        m.update({col: fmt for col, val in df.dtypes.to_dict().items() if str(val)==key})
    
    return m

def apply_formats(style, formats):
    # apply other formats that may not be defaults
    m = format_dtype(df=style.data, formats=formats)
    return style.format(m)

def defaut_number_format(x):
    # give default number format to vals in the 'numeric col mask', handle nulls
    if not pd.isnull(x):
        return f'{x:,.0f}' if x > 1e3 else f'{x:,.2f}'
    else:
        return ''

def format_date(x):
    return f'{x:%Y-%m-%d}' if not pd.isnull(x) else ''

def format_datetime(x):
    return f'{x:%Y-%m-%d  %H:%M}' if not pd.isnull(x) else ''

def alternating_rows(style):
    s = []
    s.append(dict(
        selector='tbody tr:nth-child(even)',
        props=[('background-color', '#E4E4E4')]))
    
    return style.pipe(add_table_style, s)

def alternating_rows_outlook(style, outlook=True):
    """Highlight odd rows background color grey
    - row slice is list of index labels"""

    # NOTE both of these work!! just need to pass the SLICE of INDEX as first arg, not df itself
    # subset = pd.IndexSlice[style.data.iloc[1::2].index, :]
    subset = pd.IndexSlice[style.data.index[1::2], :]

    if outlook:
        style = style.apply(
            lambda df: pd.DataFrame(data='background-color: #E4E4E4;', index=df.index, columns=df.columns), 
            subset=subset,
            axis=None)

    return style

def add_table_style(style, s, do=True):
    if not do: return style

    if not style.table_styles is None:
        style.table_styles.extend(s)
    else:
        style.set_table_styles(s)
    return style

def add_table_attributes(style, s, do=True):
    # NOTE this may not work with multiple of same attrs eg style=red, style=10px
    if not do: return style

    attrs = style.table_attributes
    if not attrs is None:
        s = f'{attrs} {s}'

    style.set_table_attributes(s)
    return style

def attrs_to_string(m):
    # convert dict of table attrs to string
    return

def string_to_attrs(s):
    # convert string of table attrs to dict
    # split on '=' and make dict of {odds: evens}
    lst = s.split('=')
    return dict(zip(lst[::2], lst[1::2]))

def set_col_alignment(style, col_name, alignment):
    i = style.data.columns.get_loc(col_name)
    s =[dict(
        selector=f'td:nth-child({i + 1})', # css table 1-indexed not 0
        props=[('text-align', alignment)])]

    return style \
        .pipe(add_table_style, s)

def set_column_style(mask, props):
    # loop columns in mask, get index, set column style
    s = []
    for i, v in enumerate(mask):
        if v == True:
            s.append(dict(
                selector=f'td:nth-child({i + 1})', # css table 1-indexed not 0
                props=[props]))

    return s

def set_column_widths(style, vals, hidden_index=True, outlook=False):
    # vals is dict of col_name: width > {'Column Name': 200}
    s = []
    offset = 1 if hidden_index else 0

    if not outlook:
        for col_name, width in vals.items():

            # some tables have different cols for monthly/weekly (F300 SMR)
            if col_name in style.data.columns:
                icol = style.data.columns.get_loc(col_name) + offset
                s.append(dict(
                    selector=f'th.col_heading:nth-child({icol})',
                    props=[('width', f'{width}px')]))
    
        return style.pipe(add_table_style, s)
    
    else: 
        # outlook - need to apply width to each cell individually
        return style.apply(col_width_outlook, axis=None, vals=vals)

def default_style(df, outlook=False):
    """Dataframe general column alignment/number formatting"""
    
    # allow passing in styler or df
    if isinstance(df, pd.io.formats.style.Styler):
        df = df.data
        
    cols = [k for k, v in df.dtypes.items() if v=='object'] # only convert for object cols
    df[cols] = df[cols].replace('\n', '<br>', regex=True)

    font_family = 'Tahoma, Geneva, sans-serif;' if not outlook else 'Calibri'

    s = []
    m = f.config['color']

    # thead selects entire header row, instead of individual header cells. Not sure if works for outlook
    s.append(dict(
        selector='thead',
        props=[('text-align', 'center'), ('background', m['thead'])]))
    s.append(dict(
        selector='th, td',
        props=[('font-family', font_family), ('padding', '2.5px 5px')]))
    s.append(dict(
        selector='table',
        props=[('border', '1px solid #000000'), ('margin-top', '0px'), ('margin-bottom', '2px')]))

    def is_np(item):
        return issubclass(type(item), np.dtype)

    # numeric_mask = df.dtypes.apply(lambda x: is_np(x) and issubclass(np.dtype(str(x).lower()).type, np.number))
    numeric_mask = df.dtypes.apply(lambda x: pd.api.types.is_numeric_dtype(x))
    date_mask = df.dtypes.apply(lambda x: is_np(x) and issubclass(np.dtype(str(x).lower()).type, np.datetime64))
    
    s.extend(set_column_style(mask=numeric_mask, props=('text-align', 'right')))
    s.extend(set_column_style(mask=~numeric_mask, props=('text-align', 'left')))
    s.extend(set_column_style(mask=date_mask, props=('text-align', 'center')))

    border = ' border: 1px solid #000000;' if outlook else ''
    table_attrs = f'style="border-collapse: collapse;{border}"'

    # NOTE kinda messy/duplicated here
    formats = {'Int64': '{:,}', 'int64': '{:,}', 'datetime64[ns]': '{:%Y-%m-%d}'}
    m_fmt = format_dtype(df=df, formats=formats)

    style = df.style \
        .format(defaut_number_format, subset=pd.IndexSlice[:, df.columns[numeric_mask]]) \
        .format(m_fmt) \
        .pipe(add_table_style, s) \
        .pipe(alternating_rows_outlook, outlook=outlook) \
        .pipe(add_table_attributes, s=table_attrs) \
        .set_na_rep('')
    
    return style


def df_empty(df):
    return pd.DataFrame(data='background-color: inherit', index=df.index, columns=df.columns)

def hide_headers(style):
    # use css selector to hide table headers
    s = []
    s = [dict(selector='.col_heading',
            props=[('display', 'none')])]
    return style.pipe(add_table_style, s)

def col_width_outlook(df, vals):
    df1 = df_empty(df)
    for col, width in vals.items():
        df1[col] = f'width: {width};'

    return df1

def get_defaults(theme):
    if theme == 'light': # reporting + emailing
        return 'inherit', 'black'
    elif theme == 'dark': # GUI
        return '', ''

def format_cell(bg, t='black'):
    return f'background-color: {bg};color: {t};'

def highlight_greater(df, ma_target):
    # Highlight cells good or bad where MA > MA Target
    # pass ma_target series separately to not apply any styles
    m = f.config['color']
    bg, t = m['bg'], m['text']

    m = df['MA'] > ma_target

    df1 = pd.DataFrame(index=df.index, columns=df.columns)
    result = np.where(m, format_cell(bg['good'], t['good']), format_cell(bg['bad'], t['bad']))
    for col in df1.columns:
        df1[col] = result
    
    # for col in ('Unit', 'Target Hrs Variance'):
    #     if col in df.columns:
    #         df1[col] = df1['MA']
    return df1

def highlight_yn(df, color_good='good', theme='light'):
    m = f.config['color']
    bg, t = m['bg'], m['text']
    default_bg, default_t = get_defaults(theme)

    m1, m2, m3 = df=='Y', df=='N', df=='S' # create three boolean masks

    where = np.where
    data = where(
        m1,
        format_cell(bg[color_good], t[color_good]),
        where(
            m2,
            format_cell(bg['bad'], t['bad']),
            where(
                m3,
                format_cell(bg['lightyellow'], 'black'),
                    f'background-color: {default_bg}')))

    return pd.DataFrame(data=data, index=df.index, columns=df.columns)

def highlight_multiple_vals(df, m : dict, convert=False, theme='light'):
    """Highlight multiple vals in df based on input from style.apply
    
    Parameters
    ----------
    m : dict
        {val: (bg_color, t_color)}
    convert : bool
        if true, convert color map to bg/text first
    """
    if convert:
        m = convert_color_code(m_color=m, theme=theme)

    m.update({None: ('inherit', 'inherit')})
    m_replace = {k: format_cell(bg=v[0], t=v[1]) for k, v in m.items()}

    return df.replace(m_replace)

def highlight_flags(df, m, suffix='_fg'):
    """Highlight flagged columns for oil samples"""
    df1 = highlight_multiple_vals(df=df, m=m)

    flagged_cols = [col for col in df.columns if suffix in col]

    for col in flagged_cols:
        col2 = col.replace(suffix, '')
        df1[col2] = df1[col]
        df1[col] = ''

    return df1

def highlight_expiry_dates(s, theme='light'):
    """Highlight FC Dates approaching expiry
    
    Parameters
    ---------
    s : pd.Series
        Only fmt single column at a time for now\n
    theme : str
        Dark or light theme for app or reports
    """
    m = f.config['color']
    bg, t = m['bg'], m['text']

    s1 = pd.Series(index=s.index) # blank series
    s_days_exp = (dt.now() - s).dt.days # days as int btwn now and date in column

    # filter column where date falls btwn range
    s1[s_days_exp.between(-90, -30)] = format_cell(bg['lightyellow'], 'black')
    s1[s_days_exp.between(-30, 0)] = format_cell(bg['lightorange'], 'black')
    s1[s_days_exp > 0] = format_cell(bg['lightred'], 'white')
    s1[s1.isnull()] = format_cell(*get_defaults(theme)) # default for everything else

    return s1

def highlight_val(df, val, bg_color, target_col, t_color=None, other_cols=None, theme='light'):
    m = f.config['color']
    bg, t = m['bg'], m['text']
    default_bg, default_t = get_defaults(theme)

    if t_color is None: t_color = 'black'

    m = df[target_col].str.lower() == val.lower()

    df1 = df_empty(df)
    df1[target_col] = np.where(m, format_cell(bg[bg_color], t[t_color]), f'background-color: {default_bg}')

    if other_cols:
        for col in other_cols:
            df1[col] = df1[target_col]

    return df1

def pipe_highlight_alternating(style, color, theme, subset=None):
    return style.apply(highlight_alternating, subset=subset, color=color, theme=theme)

def highlight_alternating(s, color='navyblue', theme='light'):
    # loop df column and switch active when value changes. Kinda ugly but works.
    # only accept single column for now
    colors = f.config['color']
    default_bg, default_t = get_defaults(theme)

    color = colors['bg'][color]
    active = 1
    prev = ''

    s1 = pd.Series(index=s.index, dtype='object') # NOTE could make this s_empty()

    # iterrows iterates tuple of (index, vals)
    for row in s.iteritems():
        idx = row[0]
        val = row[1] #[0]
        if not val == prev:
            active *= -1
        
        prev = val

        if active == 1:
            css = format_cell(bg=color, t='white')
        else:
            css = format_cell(bg=default_bg, t=default_t)

        s1.loc[idx] = css

    return s1

def highlight_totals_row(style, exclude_cols=(), n_cols=1, do=True):
    # highlight the last row of given dataframe
    if not do: return style
    bg = f.config['color']['thead']
    subset = pd.IndexSlice[style.data.index[-1 * n_cols:], :]
    
    return style.apply(
        lambda x: [format_cell(bg, 'white') if not x.index[i] in exclude_cols else 'background-color: inherit' for i, v in enumerate(x)],
        subset=subset,
        axis=1)

def highlight_accepted_loads(df):
    m = f.config['color']
    bg, t = m['bg'], m['text']

    m = df < 0.1 # highlight less than 10% good

    data = np.where(m, format_cell(bg['goodgreen'], t['goodgreen']), format_cell(bg['bad'], t['bad']))

    return pd.DataFrame(data=data, index=df.index, columns=df.columns)

def bold_columns(df):
    return pd.DataFrame(data='font-weight: bold;', index=df.index, columns=df.columns)

def set_borders(style):
    s = [dict(
        selector=f'th, td',
        props=[
            ('border', '1px solid black'),
            ('padding', '3px, 5px')])]
    return style.pipe(add_table_style, s=s)

def write_html(html, name=None):
    if name is None:
        name = 'temp'
    
    p = f.topfolder.parent / f'{name}.html'
    with open(str(p), 'w+') as file:
        file.write(html)

def convert_color_code(m_color : dict, theme : str='light'):
    """Convert color names to bg/text color codes from config
    - used to pass in to highlight_multiple_vals
    
    Parameters
    ---------
    m_color : dict
        dict of named color vals eg {'S1 Service': 'lightyellow'}
    """
    m = f.config['color']
    bg, t = m['bg'], m['text']
    default_bg, default_t = get_defaults(theme)

    return {k: (bg.get(v, default_bg), t.get(v, default_t)) for k, v in m_color.items()}
