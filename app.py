import dash
from dash import html, dash_table, dcc, Input, Output, State, ALL

app = dash.Dash(__name__)

question_style = {
    'padding': '20px',
    'backgroundColor': '#f8f9fa',
    'borderRadius': '12px',
    'marginBottom': '30px',
    'border': '1px solid #ddd',
    'boxShadow': '0 4px 6px rgba(0,0,0,0.05)'
}

input_style = {'width': '100%', 'marginBottom': '10px'}

var_columns = [
    {'name': 'Name', 'id': 'var_name', 'type': 'text'},
    {'name': 'Type', 'id': 'var_type', 'presentation': 'dropdown'},
    {'name': 'Indices', 'id': 'num_indices', 'type': 'numeric'},
    {'name': 'Index Range', 'id': 'index_range', 'type': 'text'},
    {'name': 'Unit', 'id': 'unit_num'},
]
variable_table = dash_table.DataTable(
    id='var-table',
    columns=var_columns,
    data=[],
    editable=True,
    row_deletable=True,
    style_table={'overflowX': 'auto'},
    dropdown={'var_type': {'options': [{'label': i, 'value': i} for i in ['Continuous', 'Integer', 'Binary']]}}
)

param_columns = [
    {'name': 'Name', 'id': 'var_name', 'type': 'text'},
    {'name': 'Value', 'id': 'value', 'type': 'numeric'},
    {'name': 'Indices', 'id': 'num_indices', 'type': 'numeric'},
    {'name': 'Index Range', 'id': 'index_range', 'type': 'text'},
    {'name': 'Unit', 'id': 'unit_num'},
]
parameter_table = dash_table.DataTable(
    id='param-table',
    columns=param_columns,
    data=[],
    editable=True,
    row_deletable=True,
    style_table={'overflowX': 'auto'},
    style_data_conditional=[{
        'if': {'column_id': 'value', 'filter_query': '{num_indices} > 0'},
        'backgroundColor': '#e9ecef', 'color': 'transparent', 'pointer-events': 'none'
    }]
)

app.layout = html.Div([
    html.H1("🧙‍♂️ OptiMystic Solver", style={'textAlign': 'center', 'marginBottom': '30px'}),

    html.Div([
        html.H3("1. Data Definition"),
        
        html.Div([
            html.Label("Q1. Data Type", style={'fontWeight': 'bold'}),
            dcc.RadioItems(
                id='input-category',
                options=[
                    {'label': ' Variable (Decision Variable)', 'value': 'var'},
                    {'label': ' Parameter (Constant)', 'value': 'param'}
                ],
                value='var',
                inline=True,
                style={'marginBottom': '15px'}
            ),

            html.Div([
                html.Div([
                    html.Label("Q2. Name", style={'fontWeight': 'bold'}),
                    dcc.Input(id='input-name', type='text', placeholder='e.g., Production', style=input_style),
                ], style={'width': '48%', 'display': 'inline-block', 'marginRight': '4%'}),
                html.Div([
                    html.Label("Q3. Unit", style={'fontWeight': 'bold'}),
                    dcc.Input(id='input-unit', type='text', placeholder='e.g., kg, EA', style=input_style),
                ], style={'width': '48%', 'display': 'inline-block'}),
            ]),

            html.Label("Q4. Index Settings", style={'fontWeight': 'bold', 'marginTop': '10px'}),
            dcc.RadioItems(
                id='input-is-indexed',
                options=[{'label': ' No (Scalar)', 'value': 'no'}, {'label': ' Yes (Array)', 'value': 'yes'}],
                value='no',
                inline=True
            ),
            
            html.Div(id='index-config-area', children=[
                html.Label("↳ Number of Dimensions (1~5)", style={'fontSize': '14px', 'marginTop': '5px'}),
                dcc.Input(id='input-num-indices', type='number', value=1, min=1, max=5, style={'width': '80px', 'marginLeft': '10px'}),
                html.Div(id='dynamic-index-inputs', style={'marginTop': '10px', 'padding': '10px', 'backgroundColor': '#eee', 'borderRadius': '5px'})
            ], style={'display': 'none', 'marginBottom': '15px'}),

            html.Div(id='value-input-container', children=[
                html.Label("Q5. Value (Constant)", style={'fontWeight': 'bold', 'marginTop': '10px'}),
                dcc.Input(id='input-value', type='number', placeholder='Enter number', style=input_style)
            ], style={'display': 'none'}),

            html.Div(id='type-input-container', children=[
                html.Label("Q5. Variable Type", style={'fontWeight': 'bold', 'marginTop': '10px'}),
                dcc.Dropdown(
                    id='input-var-type',
                    options=[{'label': i, 'value': i} for i in ['Continuous', 'Integer', 'Binary']],
                    value='Continuous',
                    style={'marginBottom': '15px'}
                )
            ], style={'display': 'block'}),

            html.Button("⬇️ Add to Table", id='submit-btn', n_clicks=0, 
                        style={'width': '100%', 'backgroundColor': '#007bff', 'color': 'white', 'padding': '12px', 'border': 'none', 'borderRadius': '5px', 'marginTop': '10px', 'fontWeight': 'bold'})

        ], style=question_style),
        
        html.Div(id='msg-output', style={'marginBottom': '20px', 'textAlign': 'center', 'fontWeight': 'bold'}),

        dcc.Tabs(id='main-tabs', value='tab-var', children=[
            dcc.Tab(label='📋 Variables', value='tab-var', children=[html.Div([variable_table], style={'padding': '20px'})]),
            dcc.Tab(label='🔢 Parameters', value='tab-param', children=[html.Div([parameter_table], style={'padding': '20px'})])
        ])

    ], style={'marginBottom': '50px'}),

    html.Hr(style={'borderTop': '2px dashed #bbb'}),

    html.Div([
        html.H3("2. Optimization Modeling", style={'marginTop': '30px'}),
        
        html.Label("🎯 Objective Function", style={'fontWeight': 'bold', 'fontSize': '18px'}),
        html.Div([
            dcc.Dropdown(id='objective-type', options=[{'label': 'Minimize (MIN)', 'value': 'MIN'}, {'label': 'Maximize (MAX)', 'value': 'MAX'}], value='MIN', style={'width': '30%', 'display': 'inline-block'}),
            dcc.Input(id='objective-formula', type='text', placeholder='e.g., SUM(Production[i] * Cost[i])', style={'width': '68%', 'display': 'inline-block', 'marginLeft': '2%', 'height': '36px'})
        ], style={'marginBottom': '20px'}),

        html.Label("🔒 Constraints", style={'fontWeight': 'bold', 'fontSize': '18px'}),
        dcc.Textarea(
            id='constraints-formula',
            placeholder='Enter one constraint per line.\ne.g., SUM(Production) <= Budget\nProduction[i] >= 10',
            style={'width': '100%', 'height': 150, 'marginTop': '5px', 'fontFamily': 'monospace'}
        ),
        
        html.Button("🚀 Run Solver", id='solve-btn', n_clicks=0, 
                    style={'width': '100%', 'marginTop': '30px', 'backgroundColor': '#28a745', 'color': 'white', 'padding': '15px', 'fontSize': '20px', 'border': 'none', 'borderRadius': '8px', 'cursor': 'pointer'}),
        
        html.Div(id='solver-output', style={'marginTop': '20px', 'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '5px', 'minHeight': '100px', 'backgroundColor': '#f1f1f1'})

    ])

], style={'maxWidth': '1000px', 'margin': 'auto', 'padding': '30px'})

@app.callback(
    [Output('index-config-area', 'style'),
     Output('value-input-container', 'style'),
     Output('type-input-container', 'style')],
    [Input('input-category', 'value'),
     Input('input-is-indexed', 'value')]
)
def toggle_visibility(category, is_indexed):
    show = {'display': 'block', 'marginBottom': '10px'}
    hide = {'display': 'none'}

    style_idx = show if is_indexed == 'yes' else hide
    style_val = show if (category == 'param' and is_indexed == 'no') else hide
    style_type = show if category == 'var' else hide

    return style_idx, style_val, style_type

@app.callback(
    Output('dynamic-index-inputs', 'children'),
    Input('input-num-indices', 'value')
)
def render_index_inputs(num):
    if not num or num < 1: return []
    inputs = []
    for i in range(num):
        inputs.append(html.Div([
            html.Label(f"📌 Range for Index {i+1} (e.g., 1..10 or Seoul,Busan):", style={'fontSize': '12px'}),
            dcc.Input(id={'type': 'idx-range-input', 'index': i}, type='text', style={'width': '100%', 'marginBottom': '5px'})
        ]))
    return inputs

@app.callback(
    [Output('var-table', 'data'),
     Output('param-table', 'data'),
     Output('msg-output', 'children'),
     Output('input-name', 'value')],
    Input('submit-btn', 'n_clicks'),
    [State('input-category', 'value'),
     State('input-name', 'value'),
     State('input-unit', 'value'),
     State('input-is-indexed', 'value'),
     State('input-num-indices', 'value'),
     State({'type': 'idx-range-input', 'index': ALL}, 'value'),
     State('input-value', 'value'),
     State('input-var-type', 'value'),
     State('var-table', 'data'),
     State('param-table', 'data')]
)
def add_row(n_clicks, category, name, unit, is_indexed, num_indices, idx_ranges_list, val, var_type, var_rows, param_rows):
    if n_clicks == 0: return dash.no_update
    if not name: return dash.no_update, dash.no_update, html.Span("❌ Please enter a name!", style={'color': 'red'}), dash.no_update

    if is_indexed == 'yes':
        final_num_indices = num_indices
        valid_ranges = [r for r in idx_ranges_list if r]
        final_range_str = ", ".join(valid_ranges)
    else:
        final_num_indices = 0
        final_range_str = ""
        
    new_row = {'var_name': name, 'unit_num': unit, 'num_indices': final_num_indices, 'index_range': final_range_str}

    if category == 'param':
        new_row['value'] = val if is_indexed == 'no' else ""
        param_rows.append(new_row)
        return var_rows, param_rows, html.Span(f"✅ Added Parameter '{name}'", style={'color': 'green'}), ""
    else:
        new_row['var_type'] = var_type
        var_rows.append(new_row)
        return var_rows, param_rows, html.Span(f"✅ Added Variable '{name}'", style={'color': 'green'}), ""

@app.callback(
    Output('solver-output', 'children'),
    Input('solve-btn', 'n_clicks'),
    [State('objective-formula', 'value'),
     State('constraints-formula', 'value')]
)
def run_solver(n_clicks, obj, const):
    if n_clicks == 0: return "Ready. Define data and click Run."
    return html.Div([
        html.H4("⚙️ Solver Initialized..."),
        html.P(f"Objective: {obj}"),
        html.P("Constraints: (Engine linkage required)"),
        html.P("⚠️ UI Only. Connect optimization engine in Phase 3.")
    ])

if __name__ == '__main__':
    app.run_server(debug=True)
