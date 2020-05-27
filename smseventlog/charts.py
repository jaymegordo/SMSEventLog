import plotly.graph_objects as go
from plotly.subplots import make_subplots

def pct(x):
    return '{:.1%}'.format(x)

def update_fig(fig, title=None):
    # set up basic fig layout for bar chart
    if not title is None:
        fig.update_layout(
            title=dict(
                y=0.97,
                x=0.5,
                text=title,
                xanchor='center',
                yanchor='top'))
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=0, b=20),
        height=500,
        width=500,
        xaxis_tickangle=-45,
        font=dict(size=8))
    
def chart_topdowns(df):
    fig = go.Figure(data=[
        go.Bar(
            name='SMS',
            x=df.Category,
            y=df.SMS,
            text=df['SMS %'].apply(lambda x: pct(x)),
            textposition='auto',
            marker_color='#265474'), ##244062
        go.Bar(
            name='Suncor',
            x=df.Category,
            y=df.Suncor,
            text=df['Suncor %'].apply(lambda x: pct(x)),
            textposition='auto',
            marker_color='#9e2121')])

    fig.update_layout(
        yaxis_title='Hours',
        barmode='stack',
        legend_orientation='h')
    
    title = 'Top 10 Downtime Categories'
    update_fig(fig, title=None)

    return fig

def chart_avail_rolling(df):
    # TODO add PA
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        name = 'Hours',
        x=df.Month,
        y=df.SumSMS,
        marker_color='#f08a37'))
    
    fig.add_trace(go.Scatter(
        name='MA Target',
        x=df.Month,
        y=df['MA Target'],
        yaxis='y2',
        mode='lines', 
        line=dict(
            color='#244062',
            dash='dash',
            width=1)))

    fig.add_trace(go.Scatter(
        name='MA',
        x=df.Month,
        y=df.MA,
        yaxis='y2',
        line=dict(  
            color='#244062',
            width=1)))

    fig.update_layout(
        yaxis_title='Downtime Hours',
        yaxis2=dict(
            title='% MA Target',
            showgrid=False,
            overlaying='y',
            fixedrange=True,
            range=[0,1]),
        xaxis_type='category',
        legend_orientation='h')

    title = '12 Month Rolling MA'
    update_fig(fig, title=None)

    return fig