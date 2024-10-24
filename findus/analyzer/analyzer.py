#!/usr/bin/env python3

import argparse
import plotly.express as px
import pandas as pd
import random
import datetime
import sqlite3
import time
import re
import sys
from operator import itemgetter
import datetime
import shutil

from os import listdir
from dash import Dash, dcc, html, dash_table, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

AS = {}
AS['directory'] = None
AS['database'] = None
AS['argv'] = None
AS['start_time'] = None

def update_legend_labels(fig,labels):
    for entry in fig.data:
        if entry['name'] in labels:
            entry['name'] = labels[entry['name']]

def get_number_of_experiments(directory, database):
    conn = sqlite3.connect(f"file:{directory}/{database}?mode=ro", uri=True)
    cursor = conn.cursor()
    query = f"SELECT COUNT(*) FROM experiments"
    cursor.execute(query)
    result = cursor.fetchone()
    row_count = result[0]
    conn.close()
    return row_count

def get_start_time(directory, database):
    conn = sqlite3.connect(f"file:{directory}/{database}?mode=ro", uri=True)
    cursor = conn.cursor()
    query = f"SELECT stime_seconds FROM metadata"
    cursor.execute(query)
    result = cursor.fetchone()
    seconds = result[0]
    conn.close()
    return seconds

def update_metadata(directory, database):

    AS['directory'] = directory
    AS['database'] = database

    conn = sqlite3.connect(f"file:{directory}/{database}?mode=ro", uri=True)
    cursor = conn.cursor()
    query = f"SELECT * FROM metadata"
    cursor.execute(query)
    result = cursor.fetchone()
    AS['start_time'] = result[0]
    conn.close()
    
    try:
        conn = sqlite3.connect(f"file:{directory}/{database}?mode=ro", uri=True)
        cursor = conn.cursor()    
        query = f"SELECT argv FROM metadata"
        cursor.execute(query)
        result = cursor.fetchone()
        AS['argv'] = result[0]
        conn.close()
    except:
        AS['argv'] = 'Missing from database'

def get_databases(directory):
    # get databases
    databases = []
    for file in listdir(directory):
        if re.search('^.*\\.sqlite$',file):
            databases.append(file)
    databases.sort(reverse=True)

    # add number of experiments
    databases_new = []
    for index in range(len(databases)):
        databases_new.append('%s (%d)' %(databases[index], get_number_of_experiments(directory, databases[index])))

    return databases_new

def run(directory, port, debug=False):
    DATABASE_DIRECTORY = directory

    if port == None:
        port = 8080

    app = Dash(__name__, external_stylesheets=[dbc.themes.LUX])
    app.css.config.serve_locally = True
    app.scripts.config.serve_locally = True

    app.layout = html.Div([
            html.Div([
                html.H4('Fault Injection Analysis'),
            ],style={'width':'80%','border-style':'none','margin':'0 auto'}),               
            html.Div([
                html.Button(f"Update", id='update-button', n_clicks=0, style={'width':'20%'}),
                html.Datalist(id="examples", children=[
                    html.Option(value="match_string(response, 'ets')"),
                    html.Option(value="match_hex(response, '661b')"),
                    html.Option(value="color = 'G'"),
                    html.Option(value="delay > 100"),
                    html.Option(value="length > 100"),
                ]),
                dcc.Input(id='query-input', type="text", list='examples', style={'width':'80%','display': 'inline-block'}, placeholder=f"SELECT * FROM experiments WHERE"),
                dcc.Dropdown(id='graph-dropdown', style={'width':'100%'}),
                html.Center([
                    dcc.Graph(id='graph', style={'width':'80%'}),
                ]),
                html.P('re.search(*, response)'),
                dcc.Input(id='recolor-green', type="text", placeholder="green", style={'width':'15%'}),
                dcc.Input(id='recolor-green-label', type="text", placeholder="green-label", style={'width':'10%'}),
                dcc.Input(id='recolor-yellow', type="text", placeholder="yellow", style={'width':'15%'}),
                dcc.Input(id='recolor-yellow-label', type="text", placeholder="yellow-label", style={'width':'10%'}),
                dcc.Input(id='recolor-magenta', type="text", placeholder="magenta", style={'width':'15%'}),
                dcc.Input(id='recolor-magenta-label', type="text", placeholder="magenta-label", style={'width':'10%'}),
                dcc.Input(id='recolor-orange', type="text", placeholder="orange", style={'width':'15%'}),
                dcc.Input(id='recolor-orange-label', type="text", placeholder="orange-label", style={'width':'10%'}),
                html.Br(),
                dcc.Input(id='recolor-cyan', type="text", placeholder="cyan", style={'width':'15%'}),
                dcc.Input(id='recolor-cyan-label', type="text", placeholder="cyan-label", style={'width':'10%'}),
                dcc.Input(id='recolor-blue', type="text", placeholder="blue", style={'width':'15%'}),
                dcc.Input(id='recolor-blue-label', type="text", placeholder="blue-label", style={'width':'10%'}),
                dcc.Input(id='recolor-black', type="text", placeholder="black", style={'width':'15%'}),
                dcc.Input(id='recolor-black-label', type="text", placeholder="black-label", style={'width':'10%'}),
                dcc.Input(id='recolor-red', type="text", placeholder="red", style={'width':'15%'}),
                dcc.Input(id='recolor-red-label', type="text", placeholder="red-label", style={'width':'10%'}),

                html.Br(),
                html.Label('Combine data?'),
                dcc.RadioItems(id='combine-data', options=['Yes', 'No'], value='Yes', inline=True),
                html.Div(id='data',style={'width':'100%', 'height':'80%', 'border-style':'none'}),
                html.Label('Arguments:'),
                html.Label('lalala', id='argv'),
            ],style={'width':'80%','border-style':'none','margin':'0 auto'}),
        ],style={'width':'100%', 'border-style':'none', 'margin-top':'100px','margin-bottom':'100px'})

    # callback for database list
    @app.callback(
        Output("argv", "children"),
        Input('update-button', 'n_clicks')
    )
    def update_argv(n_clicks):
        return AS['argv']

    # callback for database list
    @app.callback(
        Output("graph-dropdown", "options"),
        Input('update-button', 'n_clicks')
    )
    def update_dropdown(n_clicks):
        return get_databases(DATABASE_DIRECTORY)

    def percentage(val=None,total=None):
        return "{:.1%}".format(0.1234)

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

    def recolor(regex, response):
        if regex == None or len(regex) == 0:
            return False
        elif re.search(regex.encode(), response):
            return True
        else:
            return False

    # callback for database selection  
    @app.callback(
        Output('graph','figure'),
        Output('data','children'),
        Input('update-button', 'n_clicks'),
        Input('graph-dropdown', 'value'),
        State('query-input', 'value'),
        State('recolor-green', 'value'),
        State('recolor-green-label', 'value'),
        State('recolor-yellow', 'value'),
        State('recolor-yellow-label', 'value'),
        State('recolor-magenta', 'value'),
        State('recolor-magenta-label', 'value'),
        State('recolor-orange', 'value'),
        State('recolor-orange-label', 'value'),
        State('recolor-cyan', 'value'),
        State('recolor-cyan-label', 'value'),
        State('recolor-blue', 'value'),
        State('recolor-blue-label', 'value'),
        State('recolor-black', 'value'),
        State('recolor-black-label', 'value'),
        State('recolor-red', 'value'),
        State('recolor-red-label', 'value'),
        State('combine-data', 'value')
    )
    def update_graph(nr_of_clicks, database, query, green, greenlabel, yellow, yellowlabel, magenta, magentalabel, orange, orangelabel, cyan, cyanlabel, blue, bluelabel, black, blacklabel, red, redlabel, combine):
        if debug:
            now = round(time.time() * 1000)
        
        # update databse 
        if not database:
            raise PreventUpdate
        
        database = database.split(' ')[0]

        # copy database to /tmp and opening it
        print(f"Copying {database} to /tmp and opening from there")
        shutil.copyfile(f"{DATABASE_DIRECTORY}/{database}", f"/tmp/{database}")
        con = sqlite3.connect(f"file:/tmp/{database}?mode=ro", uri=True)

        con.create_function('match_string', 2, match_string)
        con.create_function('match_hex', 2, match_hex)

        # updating metadata from database
        update_metadata(DATABASE_DIRECTORY, database)

        # perform the query based on the query extension
        if query != None and query != '':
            query = f'SELECT * FROM experiments WHERE %s;' %(query)
        else:
            query = f'SELECT * FROM experiments;'

        # read stuff from database
        df = pd.read_sql(query, con)
        con.close()

        # recolor if needed
        records = df.to_dict('records')
        for record in records:
            if recolor(green, record['response']):
                record['color'] = 'G'
            elif recolor(yellow, record['response']):
                record['color'] = 'Y'
            elif recolor(magenta, record['response']):
                record['color'] = 'M'
            elif recolor(orange, record['response']):
                record['color'] = 'O'
            elif recolor(cyan, record['response']):
                record['color'] = 'C'
            elif recolor(blue, record['response']):
                record['color'] = 'B'
            elif recolor(black, record['response']):
                record['color'] = 'Z'
            elif recolor(red, record['response']):
                record['color'] = 'R'
        
        # create new DataFrame of recolored data
        df = pd.DataFrame.from_dict(records)

        # get amount of experiments
        nr_of_current_experiments = len(df) 

        # output plot
        fig = px.scatter(
            df,
            x = "delay", 
            y = "length",
            render_mode = "webgl",
            color = "color", 
            labels = {"color":f"Classification ({nr_of_current_experiments:,})",'delay':'delay (ns)','length':'length (ns)'},
            color_discrete_map = { 
                "G": "green",
                "Y": "yellow", 
                "M" : "magenta", 
                "O": "orange",
                "C": "cyan",
                "B": "blue",
                "Z": "black",
                "R": "red", 
            },
            category_orders = {
                "color" : ["G","Y","M","O","C","B","R"]
            }
        )

        # compute elapsed time
        # elapsed_time_in_seconds = int(time.time()-get_start_time(DATABASE_DIRECTORY, database))
        # elapsed_time = datetime.timedelta(seconds=elapsed_time_in_seconds)
        # nr_of_experiments_per_second = nr_of_current_experiments // elapsed_time_in_seconds
        
        # update title of graph
        # fig.update_layout(title_text=f"{database[:-7]} (running for {elapsed_time} @ {nr_of_experiments_per_second} per second)\n", title_x=0.5)
        fig.update_layout(title_text=f"{database[:-7]}", title_x=0.5)

        # update labels in legenda
        def make_label(color, label, df):
            count = len(df.query(f"color == '{color}'"))
            if count > 0:
                percentage = "{:.1%}".format(count/len(df))
            else:
                percentage = "{:.1%}".format(0)
            return { color: f'{label} ( {count} / {percentage} )'}

        labels = {}
        labels.update(make_label('G', greenlabel, df))
        labels.update(make_label('Y', yellowlabel, df))
        labels.update(make_label('M', magentalabel, df))
        labels.update(make_label('O', orangelabel, df))
        labels.update(make_label('C', cyanlabel, df))
        labels.update(make_label('B', bluelabel, df))
        labels.update(make_label('Z', blacklabel, df))
        labels.update(make_label('R', redlabel, df))
        update_legend_labels(fig, labels)

        # output data
        records = df.to_dict('records')

        delay_min = delay_max = length_min = length_max = 0

        # TODO: rewrite this code
        if combine == 'Yes':

            combined_records = []
            for record in records:

                # decode response to make sure it's compatible with json
                response_hex = record['response'].hex(' ')
                response = record['response'].decode('utf-8', errors='replace')

                # search for response that's already there
                for index in range(len(combined_records)):
                    if combined_records[index]['response'] == response:
                        combined_records[index]['amount'] += 1
                        
                        if record['delay'] < combined_records[index]['delayMin']:
                            combined_records[index]['delayMin'] = record['delay']

                        if record['delay'] > combined_records[index]['delayMax']:
                            combined_records[index]['delayMax'] = record['delay']

                        if record['length'] < combined_records[index]['lengthMin']:
                            combined_records[index]['lengthMin'] = record['length']

                        if record['length'] > combined_records[index]['lengthMax']:
                            combined_records[index]['lengthMax'] = record['length']
                        break
                else:
      

                    delay_min = delay_max = record['delay']
                    length_min = length_max = record['length']

                    combined_records.append({'amount': 1, 'color': record['color'], 'delayMin': delay_min, 'delayMax': delay_max, 'lengthMin': length_min, 'lengthMax': length_max, 'response': response, 'response_hex': response_hex})

            # sort new list based on occurrences 
            combined_records = sorted(combined_records, key=itemgetter('amount'), reverse=True)

            columns = ['amount', 'color', 'delayMin', 'delayMax', 'lengthMin', 'lengthMax', 'response', 'response_hex' ]

            cell_style = [
                {'if': {'column_id': 'amount'},     'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'color'},      'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'delayMin'},   'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'delayMax'},   'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'lengthMin'},  'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'lengthMax'},  'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'response'},   'textAlign': 'left'},
                {'if': {'column_id': 'response_hex'},     'textAlign': 'left'}
            ]

            nr_of_fixed_columns = 6

            records = combined_records
 
        else:
            columns = ['id', 'color', 'delay', 'length', 'rlen', 'response','response_hex']

            all_records = []

            for record in records:
                new_record = {}
                new_record['id'] = record['id']
                new_record['delay'] = record['delay']
                new_record['length'] = record['length']
                new_record['color'] = record['color']
                new_record['rlen'] = len(record['response'])
                new_record['response'] = record['response'].decode('utf-8', errors='replace')
                new_record['response_hex'] = record['response'].hex(' ')
                all_records.append(new_record)

            cell_style = [
                {'if': {'column_id': 'id'},         'textAlign': 'center','width':'100px', 'minWidth':'100px'},
                {'if': {'column_id': 'delay'},      'textAlign': 'center','width':'100px', 'minWidth':'100px'},
                {'if': {'column_id': 'length'},     'textAlign': 'center','width':'100px', 'minWidth':'100px'},
                {'if': {'column_id': 'color'},      'textAlign': 'center','width':'100px', 'minWidth':'100px'},
                {'if': {'column_id': 'rlen'},     'textAlign': 'center','width':'100px', 'minWidth':'100px'},
                {'if': {'column_id': 'response'},   'textAlign': 'left'},
                {'if': {'column_id': 'response_hex'},     'textAlign': 'left'},
            ]

            nr_of_fixed_columns = 5
            records = all_records

        data_style = [
            {'if': {'filter_query': '{color} = G'},'backgroundColor': 'green','color': 'white'},
            {'if': {'filter_query': '{color} = Y'},'backgroundColor': 'yellow','color': 'black'},
            {'if': {'filter_query': '{color} = M'},'backgroundColor': 'magenta','color': 'white'},
            {'if': {'filter_query': '{color} = O'},'backgroundColor': 'orange','color': 'white'},
            {'if': {'filter_query': '{color} = C'},'backgroundColor': 'cyan','color': 'white'},
            {'if': {'filter_query': '{color} = B'},'backgroundColor': 'blue','color': 'white'},
            {'if': {'filter_query': '{color} = Z'},'backgroundColor': 'black','color': 'white'},
            {'if': {'filter_query': '{color} = R'},'backgroundColor': 'red','color': 'white'}
        ]

        data = dash_table.DataTable(
            id='table',
            columns=[{"name": i, "id": i} for i in columns],
            data=records,
            filter_action='native',
            sort_action="native",
            page_action='native',
            page_size=30,
            fixed_columns={'headers': True, 'data': nr_of_fixed_columns},
            style_table={'overflowX': 'auto','minWidth':'100%'},
            style_cell_conditional=cell_style,
            style_data_conditional=data_style
        )

        if debug:
            done = round(time.time() * 1000)
            print('It took %d miliseconds to generate this data.' %(done - now))

        return fig,data

    # start server on localhost
    app.run_server(host='127.0.0.1', port=port, debug=True)

def main(argv=sys.argv):
    __version__ = "0.1"

    parser = argparse.ArgumentParser(
        description="analyzer.py v%s - Fault Injection Analyzer" % __version__,
        prog="analyzer"
    ) 
    parser.add_argument("--directory",help="Database directory", required=True)
    parser.add_argument("--port",help="Server port")

    args = parser.parse_args()
    run(args.directory, args.port,debug=True)

if __name__ == "__main__":
    main()