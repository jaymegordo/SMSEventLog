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
                selector=f'td:nth-child({i + 1})', # css table 1-indexed not 0
                props=[props]))

    return s

def set_column_widths(style, vals, hidden_index=True):
    # vals is dict of col_name: width > {'Column Name': 200}
    s = []
    offset = 1 if hidden_index else 0

    for col_name, width in vals.items():
        icol = style.data.columns.get_loc(col_name) + offset
        s.append(dict(
            selector=f'th.col_heading:nth-child({icol})',
            props=[('width', f'{width}px')]))
    
    style.table_styles.extend(s)
    return style

def set_style(df):
    # Dataframe general column alignment/number formatting
    cols = [k for k, v in df.dtypes.items() if v=='object'] # only convert for object cols
    df[cols] = df[cols].replace('\n', '<br>', regex=True)

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
        props=[('border', '1px solid #000000'), ('margin-top', '0px'), ('margin-bottom', '2px')]))

    numeric_mask = df.dtypes.apply(lambda x: issubclass(np.dtype(str(x).lower()).type, np.number))
    date_mask = df.dtypes.apply(lambda x: issubclass(np.dtype(str(x).lower()).type, np.datetime64))
    
    s.extend(set_column_style(mask=numeric_mask, props=('text-align', 'right')))
    s.extend(set_column_style(mask=~numeric_mask, props=('text-align', 'left')))
    s.extend(set_column_style(mask=date_mask, props=('text-align', 'center')))

    # Style 265474
    style = df.style \
        .format(lambda x: '{:,.0f}'.format(x) if x > 1e3 else '{:,.2f}'.format(x), # default number format
                    subset=pd.IndexSlice[:, df.columns[numeric_mask]])\
        .set_table_styles(s) \
        .set_table_attributes('style="border-collapse: collapse";') \
        .set_na_rep('')
    
    return style


def format_cell(bg, t='black'):
    return f'background-color: {bg};color: {t};'

def highlight_greater(df):
    # Highlight cells good or bad where MA > MA Target
    m = f.config['color']
    bg, t = m['bg'], m['text']

    m = df['MA'] > df['MA Target']

    df1 = pd.DataFrame(data='background-color: inherit', index=df.index, columns=df.columns)
    df1['MA'] = np.where(m, format_cell(bg['good'], t['good']), format_cell(bg['bad'], t['bad']))
    
    for col in ('Unit', 'Target Hrs Variance'):
        if col in df.columns:
            df1[col] = df1['MA']
    return df1

def highlight_yn(df):
    m = f.config['color']
    bg, t = m['bg'], m['text']

    m1, m2 = df=='Y', df=='N' # create two boolean masks

    where = np.where
    data = where(m1, format_cell(bg['good'], t['good']), where(m2, format_cell(bg['bad'], t['bad']), 'background-color: inherit'))

    return pd.DataFrame(data=data, index=df.index, columns=df.columns)

def highlight_val(df, val, bg_color, t_color=None, target_col='Type', other_cols=None):
    m = f.config['color']
    bg, t = m['bg'], m['text']

    if t_color is None:
        t_color = 'black'

    m = df[target_col]==val

    df1 = pd.DataFrame(data='background-color: inherit', index=df.index, columns=df.columns)

    df1[target_col] = np.where(m, format_cell(bg[bg_color], t[t_color]), 'background-color: inherit')

    if other_cols:
        for col in other_cols:
            df1[col] = df1[target_col]

    return df1

def highlight_alternating(s):
    # loop df column and switch active when value changes. Kinda ugly but works.
    # only accept single column for now
    color = f.config['color']['bg']['navyblue']
    active = 1
    prev = ''

    s1 = pd.Series(index=s.index)

    # iterrows iterates tuple of (index, vals)
    for row in s.iteritems():
        i = row[0]
        val = row[1] #[0]
        if not val == prev:
            active *= -1
        
        prev = val

        if active == 1:
            css = format_cell(bg=color, t='white')
        else:
            css = format_cell(bg='inherit')

        s1.iloc[i] = css

    return s1

# def test(row):
#     # print(row.name)
#     row['New'] = row['Unit']

# # alt_row_num = len(df.iloc[:irow + 1, icol].unique()) % 2
# df = df[:40]
# df.apply(test, axis=1)
# df