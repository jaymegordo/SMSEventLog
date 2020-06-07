import plotly.graph_objects as go
from plotly.subplots import make_subplots
from . import functions as f
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap, ListedColormap


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
            range=[0.4,1]))

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

def chart_avail_rolling(df, period='Month', title=None):
    if title is None:
        title = f'12 {period} Rolling Availability vs Downtime Hours'
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        name = 'Hours',
        x=df.Month,
        y=df.SumSMS,
        marker_color=color()['darkgrey']))
    
    fig.add_trace(go.Scatter(
        name='MA Target',
        x=df.Month,
        y=df['MA Target'],
        yaxis='y2',
        mode='lines', 
        line=dict(
            color=color()['navyblue'],
            dash='dash',
            width=1)))

    fig.add_trace(go.Scatter(
        name='MA',
        x=df.Month,
        y=df.MA,
        yaxis='y2',
        line=dict(  
            color=color()['navyblue'],
            width=1)))

    fig.add_trace(go.Scatter(
        name='PA',
        x=df.Month,
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
        legend=dict(y=-0.15))

    return fig