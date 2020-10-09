import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from plotly.subplots import make_subplots

from . import functions as f


def pct(x):
    return '{:.1%}'.format(x)

def color():
    return f.config['color']['bg']

def update_fig(fig, title=None):
    # set up basic fig layout for bar chart
    if not title is None:
        margin_top = 40
        fig.update_layout(
            title=dict(
                y=0.97,
                x=0.5,
                text=title,
                font=dict(size=16),
                xanchor='center',
                yanchor='top'))
    else:
        margin_top = 0
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=margin_top, b=20),
        height=400,
        width=400,
        xaxis_tickangle=-45,
        font=dict(size=10),
        legend_orientation='h')

def chart_fc_history(df, title=None):

    if title is None:
        title = 'Outstanding Mandatory FC History - 12 Month Rolling'

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            name='Number Outstanding FCs',
            y=df.Outstanding,
            x=df.Month,
            marker_color=color()['darkgrey'],
            offsetgroup=0))
    
    fig.add_trace(
        go.Bar(
            name='Outstanding Labour Hours',
            y=df.OutstandingHours,
            x=df.Month,
            marker_color=color()['navyblue'],
            yaxis='y2',
            offsetgroup=1
        ))

    update_fig(fig, title=title)

    fig.update_layout(
        yaxis_title='Number FCs',
        barmode='group',
        xaxis_type='category',
        bargap=0.2,
        height=350,
        width=700,
        xaxis_tickangle=-90,
        legend=dict(y=-0.3),
        yaxis2=dict(
            title='Laboour Hours'))
        
    return fig

def chart_fleet_ma(df, title=None):
    df = df.iloc[:-1] # remove totals row
    if title is None:
        title = 'Fleet MA - Actual vs Target'

    bar = go.Bar(
            name='Actual MA',
            x=df.Unit,
            y=df.MA,
            marker=dict(
                color=df.MA,
                colorscale=[color()['skyblue'], color()['navyblue']],
                cmin=0.5,
                cmax=1,
                cauto=False
                ))
    
    series = go.Scatter(
        name='MA Target',
        x=df.Unit,
        y=df['MA Target'],
        # yaxis='y2',
        mode='lines', 
        line=dict(
            color='red',
            # dash='dash',
            width=1))

    data = [bar, series]
    fig = go.Figure(data=data)
    update_fig(fig, title=title)
    fig.update_layout(
        height=350,
        width=700,
        xaxis_tickangle=-90,
        legend=dict(y=-0.2),
        yaxis=dict(
            tickformat=',.0%',
            range=[0,1]))

    return fig

def chart_topdowns(df, title=None):
    if title is None:
        title = 'Top 10 Downtime Categories'

    fig = go.Figure(data=[
        go.Bar(
            name='SMS',
            x=df.Category,
            y=df.SMS,
            text=df['SMS %'].apply(lambda x: pct(x)),
            textposition='auto',
            marker_color=color()['navyblue']), ##244062
        go.Bar(
            name='Suncor',
            x=df.Category,
            y=df.Suncor,
            text=df['Suncor %'].apply(lambda x: pct(x)),
            textposition='auto',
            marker_color=color()['maroon'])])

    update_fig(fig, title=title)

    fig.update_layout(
        yaxis_title='Hours',
        barmode='stack',
        legend=dict(y=-0.3),
        margin=dict(r=0))
    
    return fig

def chart_avail_rolling(df, period_type='month', title=None):
    if title is None:
        title = f'12 {period_type.title()} Rolling Availability vs Downtime Hours'
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        name = 'Hours',
        x=df.Period,
        y=df.SumSMS,
        marker_color=color()['darkgrey']))
    
    fig.add_trace(go.Scatter(
        name='MA Target',
        x=df.Period,
        y=df['MA Target'],
        yaxis='y2',
        mode='lines', 
        line=dict(
            color=color()['navyblue'],
            dash='dash',
            width=1)))

    fig.add_trace(go.Scatter(
        name='MA',
        x=df.Period,
        y=df.MA,
        yaxis='y2',
        line=dict(  
            color=color()['navyblue'],
            width=1)))

    fig.add_trace(go.Scatter(
        name='PA',
        x=df.Period,
        y=df.PA,
        yaxis='y2',
        line=dict(  
            color=color()['maroon'],
            width=1)))

    update_fig(fig, title=title)

    fig.update_layout(
        yaxis_title='Downtime Hours',
        height=400,
        width=600,
        bargap=0.5,
        yaxis2=dict(
            title='Availability',
            showgrid=False,
            overlaying='y',
            fixedrange=True,
            range=[0,1],
            tickformat=',.0%'),
        xaxis_type='category',
        legend=dict(y=-0.25))

    return fig

def chart_frame_cracks(df, smr_bin=False, **kw):
    fig = go.Figure()
    i = -1
    # colors = px.colors.sequential.deep
    colors = px.colors.qualitative.Prism
    # colors = px.colors.cyclical.Edge

    if smr_bin:
        from operator import attrgetter

        x = 'SMR tick'
        df[x] = df['SMR Bin'].apply(attrgetter('right')) # need for sorting
        t = 'SMR Range'
        s = df['SMR Bin']
        xaxis = dict(
            ticktext=s.astype(str),
            tickvals=df[x])
    else:
        df.Month = df.Month.apply(pd.Period.to_timestamp)
        xaxis = dict(
            type='date',
            tickformat='%Y-%m',
            dtick='M1')
        x = 'Month'
        t = 'Monthly'

    for item in sorted(df.Location.unique()):
        i += 1
        df2 = df[df.Location==item]
        fig.add_trace(go.Bar(
            name=item,
            x=df2[x],
            y=df2.Count,
            marker_color=colors[i],
            text=df2.Count,
            textposition='auto',
            textfont_size=8,
            textangle=0))

    update_fig(fig, title=f'Frame Cracks ({t}) - 2018-01 - 2020-06')

    fig.update_layout(
        height=400,
        width=800,
        template='plotly',
        legend_orientation='v',
        barmode='stack',
        xaxis_tickangle=-90,
        xaxis=xaxis)
    
    return fig

def chart_comp_co(df, **kw):
    fig = go.Figure()
    df = df.copy()
    i = -1
    # colors = px.colors.sequential.deep
    colors = px.colors.qualitative.Prism
    # colors = px.colors.cyclical.Edge

    # convert period to datetime for sorting/aligning as date, but use quarter text as labels
    x = 'Quarter'
    s = df[x].copy().astype(str)
    s = s.str[:4] + '-' + s.str[4:]
    df[x] = df[x].dt.to_timestamp()
    xaxis = dict(
        ticktext=s,
        tickvals=df[x])
    
    for item in sorted(df.Component.unique()):
        i += 1
        df2 = df[df.Component==item]
        fig.add_trace(go.Bar(
            name=item,
            x=df2[x],
            y=df2.Count,
            marker_color=colors[i],
            text=df2.Count,
            textposition='auto',
            textfont_size=8,
            textangle=0))

    update_fig(fig, title=f'Component Changeout History - FH 980E')

    fig.update_layout(
        height=400,
        width=800,
        template='plotly',
        legend_orientation='v',
        barmode='stack',
        xaxis_tickangle=-90,
        xaxis=xaxis,
        yaxis=dict(
            title='Number of Changeouts'))
    
    return fig

def chart_comp_failure_rates(df, **kw):
    fig = go.Figure()
    df = df.copy()

    mask = df.Failed == True
    df_failed = df[mask]
    df_not = df[~mask]

    fig.add_trace(
        go.Bar(
            name='Not Failed',
            text=df_not.Count,
            textposition='auto',
            marker_color=color()['navyblue'],
            x=df_not['Component'],
            y=df_not['Percent'])
    )
    fig.add_trace(
        go.Bar(
            name='Failed',
            text=df_failed.Count,
            textposition='auto',
            marker_color=color()['maroon'],
            x=df_failed['Component'],
            y=df_failed['Percent'])
    )

    update_fig(fig, title=f'Component Failure Rates - FH 980E')

    fig.update_layout(
        height=400,
        width=800,
        template='plotly',
        legend_orientation='v',
        barmode='group',
        xaxis_tickangle=-45,
        yaxis=dict(
            title='Percent of Component Group',
            fixedrange=True,
            range=[0,1],
            tickformat=',.0%'))

    return fig

def chart_engine_dt(df):
    title = 'Engine Downtime'
    bar = go.Bar(
            name='Engine Downtime',
            x=df.Period,
            y=df.Total,
            marker_color=color()['navyblue'])
    
    fig = go.Figure(data=bar)
    update_fig(fig, title=title)

    fig.update_layout(
        height=400,
        width=600,
        bargap=0.5,
        xaxis=dict(
            tickangle=-90,
            title='Period (Month)'),
        yaxis=dict(
            title='Downtime Hours'),
        xaxis_type='category',
        )
        
    return fig

def chart_plm_monthly(df, title=None, **kw):
    """Chart of PLM records by month, total accepted vs >110, >120
    - Useful to quickly show any periods which may have missing data"""
    fig = go.Figure()
    df = df.copy()
    bg = color()

    m = dict(
        Accepted_100=bg['navyblue'],
        Accepted_110=bg['orange'],
        Accepted_120=bg['maroon'])

    for col in m:
        fig.add_trace(
            go.Bar(
                name=col,
                x=df.index,
                y=df[col].fillna(0),
                marker_color=m.get(col)))
    
    update_fig(fig, title=f'PLM Haul Records (Monthly)')

    xaxis = dict(
        ticktext=df.index.to_period().astype(str),
        tickvals=df.index)
    
    fig.update_layout(
        height=400,
        width=600,
        template='plotly',
        legend_orientation='v',
        barmode='stack',
        xaxis_tickangle=-90,
        xaxis=xaxis,
        yaxis=dict(
            title='Payload Records'))

    return fig