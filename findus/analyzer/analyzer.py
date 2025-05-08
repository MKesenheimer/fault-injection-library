#!/usr/bin/env python3

import argparse
import plotly.express as px
import pandas as pd
#import datetime
import sqlite3
import time
import re
import sys
from operator import itemgetter
import shutil
import numpy as np
from itertools import product
from dataclasses import dataclass

from os import listdir
from dash import Dash, dcc, html, dash_table, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

AS = {}
AS['directory'] = None
AS['database'] = None
AS['argv'] = None
AS['start_time'] = None

def update_legend_labels(fig, labels):
    for entry in fig.data:
        if entry['name'] in labels:
            entry['name'] = labels[entry['name']]

def get_number_of_experiments(directory, database):
    conn = sqlite3.connect(f"file:{directory}/{database}?mode=ro", uri=True)
    cursor = conn.cursor()
    query = "SELECT COUNT(*) FROM experiments"
    cursor.execute(query)
    result = cursor.fetchone()
    row_count = result[0]
    conn.close()
    return row_count

def get_start_time(directory, database):
    conn = sqlite3.connect(f"file:{directory}/{database}?mode=ro", uri=True)
    cursor = conn.cursor()
    query = "SELECT stime_seconds FROM metadata"
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
    query = "SELECT * FROM metadata"
    cursor.execute(query)
    result = cursor.fetchone()
    AS['start_time'] = result[0]
    conn.close()
    try:
        conn = sqlite3.connect(f"file:{directory}/{database}?mode=ro", uri=True)
        cursor = conn.cursor()    
        query = "SELECT argv FROM metadata"
        cursor.execute(query)
        result = cursor.fetchone()
        AS['argv'] = result[0]
        conn.close()
    except Exception as _:
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

@dataclass
class Heatmap():
    x_number_of_bins: int = 10
    y_number_of_bins: int = 10
    color_scale:str = "findus"

def run(directory, ip="127.0.0.1", port=8080, x_axis="delay", y_axis="length", aspect_ratio=0, auto_update_interval=0, debug=False, heatmap:Heatmap=None):
    DATABASE_DIRECTORY = directory
    app = Dash(__name__, external_stylesheets=[dbc.themes.LUX])
    app.css.config.serve_locally = True
    app.scripts.config.serve_locally = True
    app.layout = html.Div([
            html.Div([
                html.H4('Fault Injection Analysis'),
            ],style={'width':'80%','border-style':'none','margin':'0 auto'}),               
            html.Div([
                html.Button("Update", id='update-button', n_clicks=0, style={'width':'20%'}),
                html.Datalist(id="examples", children=[
                    html.Option(value="match_string(response, 'ets')"),
                    html.Option(value="match_hex(response, '661b')"),
                    html.Option(value="color = 'G'"),
                    html.Option(value="length > 100"),
                    html.Option(value="delay > 100"),
                    html.Option(value="voltage = 400"),
                ]),
                dcc.Input(id='query-input', type="text", list='examples', style={'width':'80%','display': 'inline-block'}, placeholder="SELECT * FROM experiments WHERE"),
                dcc.Dropdown(id='graph-dropdown', style={'width':'100%'}),
                html.Center([
                    dcc.Graph(id='graph', style={'width':'80%'}),
                ]),
                html.Center([
                    dcc.Graph(id='graph_opt', style=({'display': 'none'} if heatmap is None else {'width':'80%'})),
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
                html.Label('argv_label', id='argv'),

                # timer for update_graph callback
                dcc.Interval(
                    id="interval-component",
                    interval=auto_update_interval * 1000,
                    n_intervals=0,
                    disabled=(auto_update_interval == 0)
                )
            ], style={'width':'80%','border-style':'none','margin':'0 auto'}),
        ], style={'width':'100%', 'border-style':'none', 'margin-top':'100px','margin-bottom':'100px'})

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
        if regex is None or len(regex) == 0:
            return False
        elif re.search(regex.encode(), response):
            return True
        else:
            return False

    # callback for database selection  
    @app.callback(
        Output('graph','figure'),
        Output('graph_opt','figure'),
        Output('data','children'),
        Input('update-button', 'n_clicks'),
        Input('graph-dropdown', 'value'),
        Input('interval-component', 'n_intervals'),
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
        State('combine-data', 'value'),
    )
    def update_graph(nr_of_clicks, database, interval, query, green, greenlabel, yellow, yellowlabel, magenta, magentalabel, orange, orangelabel, cyan, cyanlabel, blue, bluelabel, black, blacklabel, red, redlabel, combine):
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
        if query is not None and query != '':
            query = f'SELECT * FROM experiments WHERE {query};'
        else:
            query = 'SELECT * FROM experiments;'

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
            x = x_axis,
            y = y_axis,
            render_mode = "webgl",
            color = "color",
            labels = {"color":f"Classification ({nr_of_current_experiments:,})",y_axis:y_axis, x_axis:x_axis},
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
            },
        )

        fig_opt = None
        if heatmap is not None:
            # Assume x_edges and y_edges already created
            x_edges = np.linspace(df[x_axis].min(), df[x_axis].max(), heatmap.x_number_of_bins + 1, endpoint=True)
            y_edges = np.linspace(df[y_axis].min(), df[y_axis].max(), heatmap.y_number_of_bins + 1, endpoint=True)
            # include lower and upper limits
            x_edges[-1] = df[x_axis].max()
            y_edges[-1] = df[y_axis].max()
            x_step = (df[x_axis].max() - df[x_axis].min()) / (heatmap.x_number_of_bins)
            y_step = (df[y_axis].max() - df[y_axis].min()) / (heatmap.y_number_of_bins)
            x_min = df[x_axis].min() - x_step
            y_min = df[y_axis].min() - y_step
            x_edges = np.insert(x_edges, 0, x_min)
            y_edges = np.insert(y_edges, 0, y_min)

            # Bin data
            df["x_bin"] = pd.cut(df[x_axis], bins=x_edges, labels=False, include_lowest=True)
            df["y_bin"] = pd.cut(df[y_axis], bins=y_edges, labels=False, include_lowest=True)

            # Filter red only
            red_df = df[df["color"] == "R"]
            green_df = df[df["color"] == "G"]

            # Count red points in each bin
            red_counts = red_df.groupby(["x_bin", "y_bin"]).size().reset_index(name="red_count")
            green_counts = green_df.groupby(["x_bin", "y_bin"]).size().reset_index(name="green_count")

            # merge counts and calculate score
            heatmap_data = pd.merge(red_counts, green_counts, on=["x_bin", "y_bin"], how="outer").fillna(0)
            heatmap_data["score"] = heatmap_data["red_count"] / (heatmap_data["red_count"] + heatmap_data["green_count"])

            # Create all possible bin combinations
            all_bins = pd.DataFrame(list(product(range(heatmap.x_number_of_bins + 1), range(heatmap.y_number_of_bins + 1))), columns=["x_bin", "y_bin"])

            # Merge with actual data to fill missing bins
            heatmap_data = pd.merge(all_bins, heatmap_data, on=["x_bin", "y_bin"], how="left")
            heatmap_data["score"] = heatmap_data["score"].fillna(0)

            # Map bin numbers to bin centers for plotting
            x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
            y_centers = 0.5 * (y_edges[:-1] + y_edges[1:])
            heatmap_data["x"] = heatmap_data["x_bin"].map(dict(enumerate(x_centers)))
            heatmap_data["y"] = heatmap_data["y_bin"].map(dict(enumerate(y_centers)))

            if heatmap.color_scale == "findus":
                costum_scale=[
                    "#FFEECC",  # White
                    "#FFA500",  # Orange
                    "#FF0000",  # Red
                    "#FF00FF"   # Magenta
                ]
                heatmap.color_scale = costum_scale

            # Plot heatmap
            fig_opt = px.density_heatmap(
                heatmap_data,
                x="x",
                y="y",
                z="score",
                nbinsx=heatmap.x_number_of_bins + 1,
                nbinsy=heatmap.y_number_of_bins + 1,
                color_continuous_scale=heatmap.color_scale,
                labels={"score": "score", "x": x_axis, "y": y_axis}
            )

        # compute elapsed time
        # elapsed_time_in_seconds = int(time.time()-get_start_time(DATABASE_DIRECTORY, database))
        # elapsed_time = datetime.timedelta(seconds=elapsed_time_in_seconds)
        # nr_of_experiments_per_second = nr_of_current_experiments // elapsed_time_in_seconds
        
        # update title of graph
        # fig.update_layout(title_text=f"{database[:-7]} (running for {elapsed_time} @ {nr_of_experiments_per_second} per second)\n", title_x=0.5)
        if aspect_ratio != 0:
            fig.update_layout(title_text=f"{database[:-7]}", title_x=0.5, yaxis=dict(scaleanchor="x", scaleratio=aspect_ratio))
        else:
            fig.update_layout(title_text=f"{database[:-7]}", title_x=0.5)

        if fig_opt is not None:
            fig_opt.update_layout(title_text=f"{database[:-7]}", title_x=0.5)

        # calculate the average percentage and the standard deviation for every category
        # Divide the experiments carried out into sub-experiments and calculate the average 
        # quotient (xi) for each subset. Also calculate the average quotient of all experiments (mu).
        # The standard deviation can then be calculated using the following formula, where N is the number of experiments:
        # sigma = Sqrt(Sum((xi - mu)**2) / N)
        # Note that this approximation is dependent on the number of subsets the experiments are divided into (samples).
        # If the sample size is equal to 1, the standard deviation is 0.
        # If the sample size is large, the standard deviation is big and meaningless.
        # Both extreme values are not meaningful, which is why a samples size in between must be selected.
        # Select >= 10 samples for a rough estimate.
        # Select >= 30 samples for a statistically reliable estimate.
        # Select >= 100 samples for solid confidence, especially with noisy data.
        samples = 10
        bin_size = int(len(df) / samples)
        if bin_size == 0:
            bin_size = 1
        count = {'G':0, 'Y':0, 'M':0, 'O':0, 'C':0, 'B':0, 'Z':0, 'R':0}
        stddev = {'G':0, 'Y':0, 'M':0, 'O':0, 'C':0, 'B':0, 'Z':0, 'R':0}
        avg = {'G':0, 'Y':0, 'M':0, 'O':0, 'C':0, 'B':0, 'Z':0, 'R':0}
        for color in stddev:
            cnt = len(df.query(f"color == '{color}'"))
            count[color] = cnt
            if cnt > 0:
                mu = cnt / len(df) * 100
            else:
                mu = 0.0
            avg[color] = mu
            
            avg_per_bin = []
            for bins in range(0, int(len(df) / bin_size) - 1):
                subset = df[bin_size * bins:bin_size * (bins + 1)]
                cnt_subset = len(subset.query(f"color == '{color}'"))
                if cnt_subset > 0 and len(subset) > 0:
                    mu_subset = cnt_subset / len(subset)
                else:
                    mu_subset = 0.0
                avg_per_bin.append(mu_subset)
            sigma = 0
            if cnt > 0:
                for xi in avg_per_bin:
                    sigma += (xi - mu)**2 / cnt
                sigma = sigma**0.5
            stddev[color] = sigma
        #print(stddev)


        # update labels in legenda
        def make_label(color, label, df):
            return { color: f'{label} ( {count[color]} / {avg[color]:.1f} % +- {stddev[color]:.1f} % )'}

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

        y_min = y_max = x_min = x_max = 0

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
                        
                        if record[y_axis] < combined_records[index]['yMin']:
                            combined_records[index]['yMin'] = record[y_axis]

                        if record[y_axis] > combined_records[index]['yMax']:
                            combined_records[index]['yMax'] = record[y_axis]

                        if record[x_axis] < combined_records[index]['xMin']:
                            combined_records[index]['xMin'] = record[x_axis]

                        if record[x_axis] > combined_records[index]['xMax']:
                            combined_records[index]['xMax'] = record[x_axis]
                        break
                else:
      

                    y_min = y_max = record[y_axis]
                    x_min = x_max = record[x_axis]

                    combined_records.append({'amount': 1, 'color': record['color'], 'yMin': y_min, 'yMax': y_max, 'xMin': x_min, 'xMax': x_max, 'response': response, 'response_hex': response_hex})

            # sort new list based on occurrences 
            combined_records = sorted(combined_records, key=itemgetter('amount'), reverse=True)

            columns = ['amount', 'color', 'yMin', 'yMax', 'xMin', 'xMax', 'response', 'response_hex' ]

            cell_style = [
                {'if': {'column_id': 'amount'},     'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'color'},      'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'yMin'},   'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'yMax'},   'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'xMin'},  'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'xMax'},  'textAlign': 'center','width':'100px'},
                {'if': {'column_id': 'response'},   'textAlign': 'left'},
                {'if': {'column_id': 'response_hex'},     'textAlign': 'left'}
            ]

            nr_of_fixed_columns = 6

            records = combined_records
 
        else:
            columns = ['id', 'color', y_axis, x_axis, 'rlen', 'response','response_hex']
            all_records = []

            for record in records:
                new_record = {}
                new_record['id'] = record['id']
                new_record[y_axis] = record[y_axis]
                new_record[x_axis] = record[x_axis]
                new_record['color'] = record['color']
                new_record['rlen'] = len(record['response'])
                new_record['response'] = record['response'].decode('utf-8', errors='replace')
                new_record['response_hex'] = record['response'].hex(' ')
                all_records.append(new_record)

            cell_style = [
                {'if': {'column_id': 'id'},         'textAlign': 'center','width':'100px', 'minWidth':'100px'},
                {'if': {'column_id': y_axis},      'textAlign': 'center','width':'100px', 'minWidth':'100px'},
                {'if': {'column_id': x_axis},     'textAlign': 'center','width':'100px', 'minWidth':'100px'},
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
            print('It took %d milliseconds to generate this data.' %(done - now))

        return fig, fig_opt, data

    # start server on localhost
    app.run(host=ip, port=port, debug=True)

def main(argv=sys.argv):
    __version__ = "0.1"

    parser = argparse.ArgumentParser(
        description="analyzer.py v%s - Fault Injection Analyzer" % __version__,
        prog="analyzer"
    ) 
    parser.add_argument("--directory", help="Database directory", required=True)
    parser.add_argument("--port", help="Server port", required=False, default=8080)
    parser.add_argument("--ip", help="Server address", required=False, default='127.0.0.1')
    parser.add_argument("-x", help="parameter to plot on the x-axis", required=False, default='delay')
    parser.add_argument("-y", help="parameter to plot on the y-axis", required=False, default='length')
    parser.add_argument("--aspect-ratio", help="aspect ratio of the plot relative to x-axis", required=False, default=0, type=float)
    parser.add_argument("--auto-update", help="Whether to update the plot automatically. Optionally pass the update interval in seconds.", required=False, type=int, nargs='?', const=1, default=0)
    parser.add_argument("--heatmap", action="store_true", help="Generate a heat map", required=False)
    parser.add_argument("--x-number-of-bins", "--x-bins", help="Number of bins of the x-axis for the heat map", required=False, default=10, type=int)
    parser.add_argument("--y-number-of-bins", "--y-bins", help="Number of bins of the y-axis for the heat map", required=False, default=10, type=int)
    parser.add_argument("--color-scale", help="Color scale to use for the heat map (findus, Blues, Reds, Greys, PuRd, YlOrRd).", required=False, default="findus", type=str)

    args = parser.parse_args()

    heatmap = None
    if args.heatmap:
        heatmap = Heatmap(x_number_of_bins=args.x_number_of_bins, y_number_of_bins=args.y_number_of_bins, color_scale=args.color_scale)

    run(directory=args.directory, ip=args.ip, port=args.port, x_axis=args.x, y_axis=args.y, aspect_ratio=args.aspect_ratio, auto_update_interval=args.auto_update, heatmap=heatmap, debug=True)

if __name__ == "__main__":
    main()
