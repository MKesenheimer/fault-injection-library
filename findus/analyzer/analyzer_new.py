#!/usr/bin/env python3
# This file is based on TAoFI-Analyzer which is released under the GPL3 license.
# Go to https://github.com/raelize/TAoFI-Analyzer/LICENSE for full license details.

import argparse
from argparse import RawTextHelpFormatter
import plotly.express as px
import pandas as pd
import sqlite3
import re
import sys
from operator import itemgetter
from contextlib import closing
import os
import json
import base64

from dataclasses import dataclass, asdict, field
from dataclasses_json import dataclass_json
from typing import Dict

from os import listdir
from dash import Dash, dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash import callback_context as ctx

from dash_ag_grid import AgGrid

_RECORDS = None
_COLORS = ['green', 'yellow', 'magenta', 'orange', 'cyan', 'blue', 'black', 'red']

_COLOR_CONFIG = {
    'P': ('pink', 'black', 'timeout'),
    'G': ('green', 'white', 'green'),
    'Y': ('yellow', 'black', 'yellow'),
    'M': ('magenta', 'white', 'magenta'),
    'O': ('orange', 'white', 'orange'),
    'C': ('cyan', 'white', 'cyan'),
    'B': ('blue', 'white', 'blue'),
    'Z': ('black', 'white', 'black'),
    'R': ('red', 'white', 'red')
}

@dataclass_json
@dataclass
class AnalyzerConfig:
    serverip: str = "127.0.0.1"
    serverport: int = 8080
    directory: str = None
    database: str = None
    y: str = None
    x: str = None
    argv: str = None
    database: str = None
    query: str = ''
    colors: Dict[str, str] = field(default_factory=dict)

def update_legend_labels(fig,labels):
    for entry in fig.data:
        if entry['name'] in labels:
            entry['name'] = labels[entry['name']]

def get_number_of_experiments(directory, database):
    database_path = os.path.join(directory, database)

    try:
        with closing(sqlite3.connect(database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("SELECT COUNT(*) FROM experiments")
                return cursor.fetchone()[0]
    except Exception as e:
        print("ERROR (get_number_of_experiments): %s" %(e))

# TODO: add date
def get_databases(directory):
    # get all databases in directory
    databases = []
    for file in listdir(directory):
        if re.search('^.*\\.sqlite$',file):
            databases.append(file)
    databases.sort(reverse=True)

    # transform to options
    databases_options = []
    for index in range(len(databases)):
        label = "%s (%d)" %(databases[index], get_number_of_experiments(directory, databases[index]))
        databases_options.append( {'label':label, 'value': databases[index]} )

    return databases_options

def get_argv(directory, database):
    database_path = os.path.join(directory, database)

    try:
        with closing(sqlite3.connect(database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("SELECT argv FROM metadata")
                argvstr = cursor.fetchone()[0]
                return argvstr
    except Exception as e:
        print("ERROR (get_argv): %s" %(e))

def get_parameters(directory, database):
    database_path = os.path.join(directory, database)
    try:
        with closing(sqlite3.connect(database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("SELECT * FROM experiments")
                parameters = list(next(zip(*cursor.description)))
                parameters.remove('response')
                return parameters
    except Exception as e:
        print("ERROR (get_parameters): %s" %(e))

def run_app(config):
    app = Dash(__name__, external_stylesheets=[dbc.themes.LUX])
    app.css.config.serve_locally = True
    app.scripts.config.serve_locally = True

    app.layout = html.Div([
            dcc.Store(id='config-store', data=asdict(config)),
            html.Div([
                html.H4('Fault Injection Analysis'),
            ],style={'width':'80%','border-style':'none','margin':'0 auto'}),               
            html.Div([
                dbc.Card(
                    dbc.CardBody([

                        html.Div([
                            html.Button("Update", id='update-button', n_clicks=0, style={'width':'100px'}),
                            html.Datalist(id="examples", children=[
                                html.Option(value="match_string(response, 'ets')"),
                                html.Option(value="match_hex(response, '661b')"),
                                html.Option(value="color = 'G'"),
                                html.Option(value="delay > 100"),
                                html.Option(value="length > 100"),
                            ]),
                            dcc.Input(id='query-input', type="text", list='examples', value='', style={'width':'100%','display': 'inline-block'}, placeholder="SELECT * FROM experiments WHERE"),

                            dcc.Upload(
                                id="upload_data",
                                children=html.Button("Import", style={'width':'100px'}),
                                multiple=False,
                            ),

                            html.Button("Export", id='config-export-button',  style={'width':'100px', 'display': 'inline-block'}),
                            dcc.Download(id="download_data")
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    ])
                ),

                dbc.Card(
                    dbc.CardBody([
                        dcc.Dropdown(id='database-dropdown', style={'width':'100%'}, options=get_databases(config.directory)),
                        dcc.Dropdown(id='x-dropdown', style={'width':'100%'}),
                        dcc.Dropdown(id='y-dropdown', style={'width':'100%'})
                    ])
                ),
                dbc.Card(
                    dbc.CardBody([
                        html.Center([
                            dcc.Graph(id='graph', style={'width':'80%'}),
                        ]),
                    ])
                ),
                dbc.Card(
                    dbc.CardBody([

                        html.P('re.search(*, response)'),

                            *(
                                input_component
                                for color in _COLORS
                                for input_component in [
                                    dcc.Input(
                                        id=f'recolor-{color}',type="text",placeholder=f"{color}", style={'width':'15%'}
                                    ),
                                    dcc.Input(
                                        id=f'recolor-{color}-label',type="text",placeholder=f"{color}-label",style={'width':'15%', 'margin-right': '10px', 'margin-bottom':'10px'}
                                    )
                                ]
                            ),
                    ])
                ),
                dbc.Card(
                    dbc.CardBody([
                        dbc.Switch(
                            id='switch-squeezedata',
                            value=False,
                            label='Squeeze Data',
                            style={'display': 'inline-block', 'marginRight': '20px'}
                        ),
                        dbc.Switch(
                            id='switch-showhexdata',
                            value=False,
                            label='Show Hex',
                            style={'display': 'inline-block'}
                        ),
                        html.Div(id='data',style={'width':'100%', 'height':'100%', 'border-style':'none'}),
                    ])
                ),
                dbc.Card([
                    dbc.CardHeader('Arguments:'),
                    dbc.CardBody([
                        dcc.Markdown('', id='argv'),
                    ])
                ]),
                dbc.Card([
                    dbc.CardHeader('Points:'),
                    dbc.CardBody([
                        dcc.Markdown('', id='points'),
                    ])
                ]),
                dbc.Card([
                    dbc.CardHeader('Store:'),
                    dbc.CardBody([
                        dcc.Markdown('', id='printstore'),
                    ])
                ]),
            ],style={'width':'80%','border-style':'none','margin':'0 auto'}),
        ],style={'width':'100%', 'border-style':'none', 'margin-top':'100px','margin-bottom':'100px'})

    # callback for zoomed doints
    @app.callback(
        Output('points', 'children'),
        [
            Input('graph', 'relayoutData'),
            Input('graph', 'figure')
        ],
        prevent_initial_call=True
    )
    def zoomed_points(relayoutData, figure):
        if not figure or 'xaxis.range[0]' not in relayoutData:
            raise PreventUpdate

        layout = figure["layout"]
        x_axis = layout["xaxis"]
        y_axis = layout["yaxis"]

        if 'xaxis.range[0]' in relayoutData:
            ranges = {
                'x': (relayoutData['xaxis.range[0]'], relayoutData['xaxis.range[1]']),
                'y': (relayoutData['yaxis.range[0]'], relayoutData['yaxis.range[1]'])
            }
        else:
            ranges = {
                'x': tuple(x_axis['range']),
                'y': tuple(y_axis['range'])
            }

        p = f'''
            * {x_axis['title']['text']}
                * {ranges['x'][0]}
                * {ranges['x'][1]}
            * {y_axis['title']['text']}
                * {ranges['y'][0]}
             * {ranges['y'][1]}
        '''

        return p

    # callback for exporting config
    @app.callback(
       Output('download_data', 'data'),
       Input('config-export-button', 'n_clicks'),
       State('config-store', 'data'),
       prevent_initial_call=True
    )
    def download(n_clicks,store):
       config = AnalyzerConfig(**store)
       return dict(content=config.to_json(), filename="config.json")

    # callback for printing store at the bottom
    @app.callback(
        Output('printstore', 'children'),
        Input('config-store', 'data')
    )
    def printstore(store):
        p = ""
        for key,value in store.items():
            p += f"* {key}:{value}\n"
        return p

    # callback for updating store
    @app.callback(
        Output('config-store', 'data'),
        Output("database-dropdown", "value"),
        Output("x-dropdown", "value"),
        Output("y-dropdown", "value"),
        [
            Input('update-button', 'n_clicks'),
            Input('upload_data', 'contents'),
            Input('query-input', 'value'),
            Input('database-dropdown', 'value'),
            Input('x-dropdown', 'value'),
            Input('y-dropdown', 'value')
        ],
        [
            State('config-store', 'data'),
        ]
    )
    def update_store(nr_of_clicks, contents, query, database, x, y, store):
        if ctx.triggered_id == 'upload_data':
            if contents:
                content_type, content_string = contents.split(',')
                config_dict = json.loads(base64.b64decode(content_string))
                config = AnalyzerConfig(**config_dict)
                update_global_records(config)
                return config_dict,config.database,config.x,config.y

        if database is None:
            raise PreventUpdate

        database = database.split(' ')[0]
        config = AnalyzerConfig(**store)
        config.database = database
        config.x = x
        config.y = y
        config.query = query
        config.argv = get_argv(config.directory, config.database)
        return asdict(config),config.database,config.x,config.y

    # callback for printing the argv string at the bottom
    @app.callback(
        Output('argv', 'children'),
        Input('config-store', 'data'),
        prevent_initial_call=True
    )
    def update_argv(store):
        config = AnalyzerConfig(**store)
        return config.argv

    # callback for x list
    @app.callback(
        Output('x-dropdown', 'options'),
        Input('database-dropdown', 'value'),
        State('config-store', 'data'),
        prevent_initial_call=True
    )
    def update_dropdown_x(database, store):
        config = AnalyzerConfig(**store)
        return get_parameters(config.directory, database)

    # callback for y list
    @app.callback(
        Output('y-dropdown', 'options'),
        Input('database-dropdown', 'value'),
        State('config-store', 'data'),
        prevent_initial_call=True
    )
    def update_dropdown_y(database, store):
        config = AnalyzerConfig(**store)
        return get_parameters(config.directory, database)

    # new function for sqlite3 query
    def match_string(response, token):
        if token.encode(errors='strict') in response:
            return True
        else:
            return False

    # new function for sqlite3 query
    def match_hex(response, token):
        if bytes.fromhex(token) in response:
            return True
        else:
            return False

    def recolor(record, regex, new_color):
        if regex in [None, '']:
            return record['color']
        elif re.search(regex.encode(), record['response']):
            return new_color
        else:
            return record['color']

    def glitch_parameter_present(record, parameter):
        if parameter in record and record[parameter] not in [0, None]:
            return True
        else:
            return False

    def generate_data(records, squeeze_records=False):
        has_length = glitch_parameter_present(records[0], 'length')
        has_power = glitch_parameter_present(records[0], 'power')

        new_records = []

        if not squeeze_records:

            for record in records:
                new_record = {}
                new_record['id'] = record['id']
                new_record['color'] = record['color']
                new_record['delay'] = record['delay']
                if has_length:
                    new_record['length'] = record['length']
                if has_power:
                    new_record['power'] = record['power']
                new_record['rlen'] = len(record['response'])
                new_record['response'] = record['response'].decode('utf-8', errors='replace')
                new_record['hex(response)'] = record['response'].hex(' ')
                new_records.append(new_record)

            return new_records
        else:

            squeezed_records = {}

            for record in records:
                response = record['response'].decode('utf-8', errors='replace')

                if response not in squeezed_records:
                    squeezed_records[response] = {}
                    squeezed_records[response]['amount'] = 1
                    squeezed_records[response]['color'] = record['color']
                    squeezed_records[response]['Min(Delay)'] = record['delay']
                    squeezed_records[response]['Max(Delay)'] = record['delay']
                    if has_length:
                        squeezed_records[response]['Min(Length)'] = record['length']
                        squeezed_records[response]['Max(Length)'] = record['length']
                    if has_power:
                        squeezed_records[response]['Min(Power)'] = record['power']
                        squeezed_records[response]['Max(Power)'] = record['power']
                    squeezed_records[response]['response'] = response
                    squeezed_records[response]['hex(response)'] = record['response'].hex(' ')
                else:
                    squeezed_records[response]['amount'] += 1
                    squeezed_records[response]['Min(Delay)'] = min(squeezed_records[response]['Min(Delay)'], record['delay'])
                    squeezed_records[response]['Max(Delay)'] = max(squeezed_records[response]['Max(Delay)'], record['delay'])
                    if has_length:
                        squeezed_records[response]['Min(Length)'] = min(squeezed_records[response]['Min(Length)'], record['length'])
                        squeezed_records[response]['Max(Length)'] = max(squeezed_records[response]['Max(Length)'], record['length'])
                    if has_power:
                        squeezed_records[response]['Min(Power)'] = min(squeezed_records[response]['Min(Power)'], record['power'])
                        squeezed_records[response]['Max(Power)'] = max(squeezed_records[response]['Max(Power)'], record['power'])

            return sorted(squeezed_records.values(), key=itemgetter('amount'), reverse=True)

    def give_xy_label(parameter):
        labels = { 'length': '(ns)', 'delay': '(ns)', 'power': '(%)' }
        return labels.get(parameter, '')

    def update_global_records(config):
        global _RECORDS

        if not os.path.isfile(f"{config.directory}/{config.database}"):
            raise PreventUpdate

        con = sqlite3.connect(f"{config.directory}/{config.database}")

        # add some functions to sqlite
        con.create_function('match_string', 2, match_string)
        con.create_function('match_hex', 2, match_hex)

        # perform the query based on the query extension
        if config.query == '':
            query = 'SELECT * FROM experiments;'
        else:
            query = f'SELECT * FROM experiments WHERE {config.query};'

        # read stuff from database
        try:
            df = pd.read_sql(query, con)
            con.close()
        except:
            raise PreventUpdate

        # store records from global
        _RECORDS = df.to_dict('records')

    # callback graph; chained from update_store()
    @app.callback(
        Output('graph','figure'),
        [Input('config-store', 'data'), Input('x-dropdown', 'value'), Input('y-dropdown', 'value')],
        [State(f'recolor-{color}', 'value') for color in _COLORS] +
        [State(f'recolor-{color}-label', 'value') for color in _COLORS],
        prevent_initial_call=True
    )
    def update_graph(store, x, y, *color_states):
        global _RECORDS

        config = AnalyzerConfig(**store)

        if ctx.triggered_id == 'config-store':
            x = config.x
            y = config.y

        # prevent update
        if any(v is None for v in [x, y]):
            raise PreventUpdate

        update_global_records(config)

        # color amounts
        colors = { 'P':0,'G':0,'Y':0,'M':0,'O':0,'C':0,'B':0,'Z':0,'R':0 }

        color_values = color_states[:8]
        color_labels = color_states[8:]

        color_map = dict(zip(_COLORS,['G', 'Y', 'M', 'O', 'C', 'B', 'Z', 'R']))

        # recolor if needed
        for record in _RECORDS:
           for value, color_code in zip(color_values, color_map.values()):
               record['color'] = recolor(record, value, color_code)
           colors[record['color']] += 1

        # output plot
        try:
            fig = px.scatter(
                _RECORDS,
                x = x,
                y = y,
                render_mode = "webgl",
                color = "color",
                labels = {
                    'color': f'Classification ({len(_RECORDS):,})',
                    x: f'{x} {give_xy_label(x)}',
                    y: f'{y} {give_xy_label(y)}'
                },
                color_discrete_map = {
                   "P": "pink", "G": "green", "Y": "yellow", "M": "magenta",
                   "O": "orange", "C": "cyan", "B": "blue", "Z": "black", "R": "red"
                },
                category_orders = {"color" : ["P", "G","Y","M","O","C","B","Z","R"]}
            )
        except:
            raise PreventUpdate

        # update title of graph
        fig.update_layout(title_text=config.database[:-7], title_x=0.5, title_y=0.95)

        if config.x == 'x' or config.y == 'y':
            fig.update_xaxes(title_standoff=0, side='top')
            fig.update_yaxes(title_standoff=0, autorange='reversed')

        # Update legend labels
        labels = {}
        for color_code, label in zip(color_map.values(), color_labels):
           count = colors[color_code]
           labels[color_code] = f'{label} ( {count} / {count/len(_RECORDS):.1%} )'
        labels['P'] = f'timeout ( {colors["P"]} / {colors["P"]/len(_RECORDS):.1%} )'
        update_legend_labels(fig, labels)

        return fig

    # callback data; chained from update_graph()
    @app.callback(
        Output('data', 'children'),
        [
            Input('config-store', 'data'),
            Input('graph', 'figure'),
            Input('switch-squeezedata', 'value'),
            Input('switch-showhexdata', 'value')
        ],
        prevent_initial_call=True
    )
    def update_data(store, figure, squeeze, showhex):
        global _RECORDS

        if any(x is None for x in [figure, _RECORDS]):
            raise PreventUpdate

        # squeeze data (or not)
        data = generate_data(_RECORDS, squeeze_records=squeeze)

        # get columns from _RECORDS
        columns = data[0].keys()

        fields = []
        configs = []

        for column in columns:
            fields.append(column)
            if column in ['id', 'color', 'delay', 'length', 'power', 'rlen']:
                configs.append({
                    'autoSize':True,
                    'maxWidth': 100,
                    'cellStyle': {'textAlign': 'center'},
                   'headerClass': 'header-center-aligned',
                   'pinned': 'left'
                })
            elif 'Max' in column or 'Min' in column or column == 'amount':
                configs.append({
                    'autoSize':True,
                    'maxWidth': 150,
                    'cellStyle': {'textAlign': 'center'},
                    'headerClass': 'header-center-aligned',
                    'pinned': 'left'
                })
            elif column in ['response']:
                configs.append({
                    'autoSize':False,
                    'width': 500,
                    'flex': 1
                })
            elif column in ['hex(response)']:
                configs.append({
                    'autoSize':False,
                    'width': 500,
                    'hide': not showhex
                })
            else:
                configs.append({'autoSize':True,})

        columnDefs = [
            {'field': field, **config}
            for field, config in zip(fields, configs)
        ]

        # getRowStyle = {
        #     "styleConditions": [
        #         {
        #             "condition": "params.data.color = 'G'",
        #             "style": {"backgroundColor": "green"},
        #         },
        #     ],
        #     "defaultStyle": {"backgroundColor": "grey", "color": "white"},
        # }

        rowstyles = {
            "styleConditions": [
                {
                    "condition": "params.data.color == 'G'",
                    "style": {"backgroundColor": "#d5f5e3"},
                },
                {
                    "condition": "params.data.color == 'R'",
                    "style": {"backgroundColor": "#fadbd8"},
                },
                {
                    "condition": "params.data.color == 'Y'",
                    "style": {"backgroundColor": "#fcf3cf"},
                },
                {
                    "condition": "params.data.color == 'B'",
                    "style": {"backgroundColor": "#d4e6f1"},
                },
                {
                    "condition": "params.data.color == 'M'",
                    "style": {"backgroundColor": "#ebdef0"},
                },
                {
                    "condition": "params.data.color == 'O'",
                    "style": {"backgroundColor": "#fae5d3"},
                },
                {
                    "condition": "params.data.color == 'Z'",
                    "style": {"backgroundColor": "#d6dbdf"},
                },
            ],
            "defaultStyle": {"backgroundColor": "white", "color": "black"}
        }

        data = AgGrid(
            columnDefs=columnDefs,
            rowData=data,
            defaultColDef={
                'resizable': True,
                'sortable': True,
                'filter': True,
                'checkboxSelection': False
            },
            className='ag-theme-quartz',
            getRowStyle=rowstyles,
            dashGridOptions= {
                # 'groupHeaderHeight': 75,
                # 'headerHeight': 150,
                # 'floatingFiltersHeight': 40,
                'pagination': True,
                'animateRows': False
            },
            style={'height': '1000px'},
        )

        return data

    app.run_server(host=config.serverip, port=config.serverport, debug=True)

def run(args):
    config = AnalyzerConfig(
        serverip=args.ip,
        serverport=args.port,
        directory=args.directory,
        x = args.x,
        y = args.y,
    )

    for color in _COLORS:
        config.colors[color] = [None,None]

    run_app(config)

def main(argv=sys.argv):
    __version__ = "2.0"

    parser = argparse.ArgumentParser(
        description="analyzer.py v%s - Fault Injection Analyzer\nThis program is based on https://github.com/raelize/TAoFI-Analyzer." % __version__,
        prog="analyzer",
        formatter_class=RawTextHelpFormatter
    ) 
    parser.add_argument("--ip",help="Server port", type=str, default="127.0.0.1")
    parser.add_argument("--port",help="Server port", type=int, default=8080)
    parser.add_argument("--directory",help="Database directorys", required=True)
    parser.add_argument("--x", required=False, help="Preset the x parameter")
    parser.add_argument("--y", required=False, help="Preset the y parameter")

    args = parser.parse_args()

    run(args)

if __name__ == "__main__":
    main()