import plotly.plotly as py
import plotly.graph_objs as go
import numpy as np
import pandas as pd
import datetime

import dash
import dash_core_components as dcc
import dash_html_components as html
import os
from dash.dependencies import Input, Output

zika = pd.read_csv('https://raw.githubusercontent.com/charleyferrari/bnext-crossfilter/master/zika.csv').drop('X', axis = 1)

countryCodes = pd.DataFrame(dict(country = ['Argentina', 'Colombia', 'Dominican_Republic', 'Ecuador',
                                            'El_Salvador', 'Mexico', 'Nicaragua', 'Panama', 'Puerto_Rico',
                                            'United_States'],
                                code = ['ARG', 'COL', 'DOM', 'ECU', 'SLV', 'MEX', 'NIC', 'PAN', 'PRI', 'USA']))

zika = pd.merge(zika, countryCodes, on='country')

reportTypes = zika['report_type'].unique()
locations = zika['location'].unique()

zika['report_date'] = zika['report_date'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d').date())

dates = [np.sort(zika['report_date'].unique())[0], np.sort(zika['report_date'].unique())[-1]]

countries = ['Argentina', 'Colombia', 'Dominican_Republic', 'Ecuador', 'El_Salvador', 'Mexico', 'Nicaragua',
             'Panama', 'Puerto_Rico', 'United_States']

types = ['confirmed', 'suspected']

locations = zika['location'].unique()

timeseriesSelected = {
    'points': [
        {
            'x': 0,
            'y': 0,
            'pointNumber': i,
            'curveNumber': 0,
            'marker.color': 'rgba(68,6,83,0.2)'
        } for i in range(47, 69)
    ]
}

subMapSelected = {
    'points': [
        {
            "pointNumber": i,
            "text": zika.loc[i, 'location'] + ': ' + str(zika.loc[i, 'value']),
            "marker.opacity": 1,
            "marker.line.width": 1,
            "marker.color": 15,
            "lon": -69.578549,
            "lat": -1.3227799999999998,
            "curveNumber": 0
        } for i,point in enumerate(range(0,len(zika)))
    ]
}


datelist = np.sort(zika['report_date'].unique())

def makeChoropleth(dates, types, countries, locations):

    chorodata = zika.loc[(zika['report_date'] >= dates[0]) & (zika['report_date'] <= dates[1]) &
                        (zika['report_type'].isin(types)) & (zika['location'].isin(locations))].copy()

    chorodata = chorodata.groupby(['code', 'country']).sum()['value'].reset_index()
    chorodata = pd.merge(zika[['code', 'country']].drop_duplicates().reset_index().drop('index', axis = 1),
                         chorodata, on=['code', 'country'], how='outer')

    chorodata = chorodata.loc[chorodata['country'].isin(countries)]

    data = [
        go.Choropleth(
            locations = chorodata['code'],
            z = chorodata['value'],
            colorscale = 'Viridis',
            zmin = 0,
            zmax = zika.groupby('country').sum()['value'].max()
        )
    ]

    layout = go.Layout(
        title = 'Zika Cases by Country',
        geo = dict(
            center = dict(lon = -60, lat = -12),
            projection = dict(scale = 2)
        )
    )

    return go.Figure(data = data, layout = layout)

def makeScatterMap(dates, types, countries, locations):

    scattermapdata = zika.loc[(zika['report_date'] >= dates[0]) & (zika['report_date'] <= dates[1]) &
                              (zika['report_type'].isin(types)) & (zika['country'].isin(countries))].copy()

    scattermapdata = scattermapdata.groupby(['location', 'lat', 'lon']).sum()['value'].reset_index()

    scattermapdata['text'] = scattermapdata.apply(lambda x: x['location'] + ': ' + str(x['value']) ,axis = 1)
    scattermapdata['opacity'] = scattermapdata['location'].apply(lambda x: 1 if x in locations else 0.2)
    scattermapdata['width'] = scattermapdata['location'].apply(lambda x: 1 if x in locations else 0)

    data = [
        go.Scattergeo(
            lat = scattermapdata['lat'],
            lon = scattermapdata['lon'],
            text = scattermapdata['text'],
            hoverinfo = 'text',
            marker = dict(
                color = scattermapdata['value'],
                colorscale = 'Viridis',
                opacity = scattermapdata['opacity'],
                line = dict(
                    width = scattermapdata['width']
                )
            )
        )
    ]

    layout = go.Layout(
        title = 'Zika Cases by Municipality',
        dragmode = 'lasso',
        geo = dict(
            center = dict(lon = -60, lat = -12),
            projection = dict(scale = 2)
        )
    )

    fig = go.Figure(data = data, layout = layout)

    return fig

def makeTimeSeriesGraph(dates, types, countries, locations):

    timeseriesdata = zika.loc[(zika['report_type'].isin(types)) & (zika['country'].isin(countries)) &
                             (zika['location'].isin(locations))]

    timeseriesdata = timeseriesdata.groupby('report_date').sum()['value'].reset_index().sort_values('report_date')

    timeseriesdata = pd.merge(pd.DataFrame(zika['report_date']).drop_duplicates().reset_index().drop('index', axis = 1),
                             timeseriesdata, on = 'report_date', how = 'outer')
    timeseriesdata = timeseriesdata.sort_values('report_date').fillna(0)

    timeseriesdata['color'] = timeseriesdata['report_date'].apply(
        lambda x: 'rgba(68,6,83,1)' if (x >= dates[0]) & (x <= dates[1]) else 'rgba(68,6,83,0.2)')

    data = [
        go.Bar(
            x = timeseriesdata['report_date'],
            y = timeseriesdata['value'],
            marker = dict(
                color = timeseriesdata['color']
            )
        )
    ]

    layout = go.Layout(title = 'Reports over time', dragmode = 'select', showlegend = False, hovermode = 'closest')

    return go.Figure(data = data, layout = layout)

app = dash.Dash(__name__)
server = app.server

app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})

app.layout = html.Div([
    html.Div([
        html.H2('Zika Explorer'),
        html.Div([], className = 'one column'),
        html.Div([
            html.Div([
                html.P('Date Range')
            ], className = 'row'),
            html.Div([
                dcc.Dropdown(
                    id = 'countryPicker',
                    options = [{'label': i, 'value': i} for i in zika['country'].unique()],
                    multi = True,
                    value = zika['country'].unique()
                )
            ], className = 'row')

        ], className = 'seven columns'),
        html.Div([
            html.Div([
                html.P('Report Type')
            ], className = 'row'),
            html.Div([
                dcc.Dropdown(
                    id = 'reportTypePicker',
                    options = [{'label': i, 'value': i} for i in zika['report_type'].unique()],
                    multi = True,
                    value = zika['report_type'].unique()
                )
            ], className = 'row')
        ], className = 'three columns'),
        html.Div([], className = 'one column')
    ], className = 'row'),
    html.Div([
        html.Div([
            dcc.Graph(id = 'countryMap', figure = makeChoropleth(dates, types, countries, locations))
        ], className = 'six columns'),
        html.Div([
            dcc.Graph(id = 'subMap', figure = makeScatterMap(dates, types, countries, locations),
                selectedData = subMapSelected)
        ], className = 'six columns')
    ], className = 'row'),
    html.Div([
        dcc.Graph(id = 'timeSeriesGraph',
            figure = makeTimeSeriesGraph(dates, types, countries, locations),
            selectedData = timeseriesSelected)
    ], className = 'row')
])

@app.callback(
    Output('countryMap', 'figure'),
    [Input('countryPicker', 'value'), Input('reportTypePicker', 'value'),
    Input('timeSeriesGraph', 'selectedData'), Input('subMap', 'selectedData')]
)
def returnChoropleth(countryList, reportTypeList, datePoints, locationPoints):
    datePointList = [i['pointNumber'] for i in datePoints['points']]
    datePointList = np.sort(datePointList)
    dates = datelist[datePointList[0]], datelist[datePointList[-1]]
    locationList = [i['text'].split(':')[0] for i in locationPoints['points']]

    return makeChoropleth(dates, reportTypeList, countryList, locationList)

@app.callback(
    Output('subMap', 'figure'),
    [Input('countryPicker', 'value'), Input('reportTypePicker', 'value'),
    Input('timeSeriesGraph', 'selectedData'), Input('subMap', 'selectedData')]
)
def returnSubMap(countryList, reportTypeList, datePoints, locationPoints):
    datePointList = [i['pointNumber'] for i in datePoints['points']]
    datePointList = np.sort(datePointList)
    dates = datelist[datePointList[0]], datelist[datePointList[-1]]
    locationList = [i['text'].split(':')[0] for i in locationPoints['points']]

    return makeScatterMap(dates, reportTypeList, countryList, locationList)

@app.callback(
    Output('timeSeriesGraph', 'figure'),
    [Input('countryPicker', 'value'), Input('reportTypePicker', 'value'),
    Input('timeSeriesGraph', 'selectedData'), Input('subMap', 'selectedData')]
)
def returnTimeSeries(countryList, reportTypeList, datePoints, locationPoints):
    datePointList = [i['pointNumber'] for i in datePoints['points']]
    datePointList = np.sort(datePointList)
    dates = datelist[datePointList[0]], datelist[datePointList[-1]]
    locationList = [i['text'].split(':')[0] for i in locationPoints['points']]

    return makeTimeSeriesGraph(dates, reportTypeList, countryList, locationList)

if __name__ == '__main__':
    app.run_server(debug=True)
