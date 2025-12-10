import dash
from dash import html, dash_table, dcc, Input, Output, State, ALL

external_stylesheets = ['https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, title='OptiMystic Solver')

app_style = {
    'fontFamily': 'Inter, sans-serif',
    'maxWidth': '1000px',
    'margin': 'auto',
    'padding': '40px 20px',
    'color': '#333'
}

question_style = {
    'padding': '25px',
    'backgroundColor': '#f8f9fa',
    'borderRadius': '12px',
    'marginBottom': '30px',
    'border': '1px solid #e9ecef',
    'boxShadow': '0 4px 12px rgba(0,0,0,0.05)'
}

input_style = {
    'width': '100%', 
    'padding': '8px', 
    'borderRadius': '4px', 
    'border': '1px solid #ccc',
    'marginBottom': '10px'
}

table_header_style = {
    'backgroundColor': '#f1f3f5',
    'fontWeight': '600',
    'border': '1px solid #dee2e6',
    'textAlign': 'left',
    'padding': '10px'
}

table_cell_style = {
    'padding': '10px',
    'border': '1px solid #dee2e6',
    'fontSize': '14px',
    'fontFamily': 'Inter, sans-serif'
}

var_columns = [
    {'name': 'Name', 'id': 'var_name', 'type': 'text'},
    {'name': 'Type', 'id': 'var_type', 'presentation': 'dropdown'},
    {'name': 'Indices', 'id': 'num_indices', 'type': 'numeric'},
    {'name': 'Index Range', 'id': 'index_range', 'type': 'text'},
    {'name': 'Unit(Num)', 'id': 'unit_num', 'type': 'text'},
    {'name': 'Unit(Denom)', 'id': 'unit_denom', 'type': 'text'},
]

variable_table = dash_table.DataTable(
    id='var-table',
    columns=var_columns,
    data=[],
    editable=True,
    row_deletable=True,
    style_table={'overflowX': 'auto', 'marginBottom': '20px'},
    style_header=table_header_style,
    style_cell=table_cell_style,
    dropdown={'var_type': {'options': [{'label': i, 'value': i} for i in ['Continuous', 'Integer', 'Binary']]}}
)

param_columns = [
    {'name': 'Name', 'id': 'var_name', 'type': 'text'},
    {'name': 'Value', 'id': 'value', 'type': 'numeric'},
    {'name': 'Indices', 'id': 'num_indices', 'type': 'numeric'},
    {'name': 'Index Range', 'id': 'index_range', 'type': 'text'},
    {'name': 'Unit(Num)', 'id': 'unit_num', 'type': 'text'},
    {'name': 'Unit(Denom)', 'id': 'unit_denom', 'type': 'text'},
]

parameter_table = dash_table.DataTable(
    id='param-table',
    columns=param_columns,
    data=[],
    editable=True,
    row_deletable=True,
    style_table={'overflowX': 'auto', 'marginBottom': '20px'},
    style_header=table_header_style,
    style_cell=table_cell_style,
    style_data_conditional=[{
        'if': {'column_id': 'value', 'filter_query': '{num_indices} > 0'},
        'backgroundColor': '#f8f9fa', 'color': 'transparent', 'pointer-events': 'none'
    }]
)

app.layout = html.Div([
    html.H1("🧙‍♂️ OptiMystic Solver", style={'textAlign': 'center', 'marginBottom': '40px', 'fontWeight': '600'}),

    dcc.Tabs(id='main-view-tabs', value='view-data', children=[
        
        dcc.Tab(label='STEP 1: Define Data', value='view-data', style={'padding': '10px', 'fontWeight': 'bold'}, selected_style={'padding': '10px', 'fontWeight': 'bold', 'borderTop': '3px solid #007bff'}, children=[
            html.Div([
                html.H3("Data Definition Wizard", style={'marginTop': '30px', 'marginBottom': '20px'}),
                
                html.Div([
                    html.Label("Data Type", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '8px'}),
                    dcc.RadioItems(
                        id='input-category',
                        options=[
                            {'label': ' Variable (Decision Variable)', 'value': 'var'},
                            {'label': ' Parameter (Constant)', 'value': 'param'}
                        ],
                        value='var',
                        inline=True,
                        style={'marginBottom': '20px'}
                    ),

                    html.Div([
                        html.Div([
                            html.Label("Name", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '8px'}),
                            dcc.Input(id='input-name', type='text', placeholder='e.g., Production', style=input_style),
                        ], style={'width': '48%', 'display': 'inline-block', 'marginRight': '4%'}),
                        
                        html.Div([
                            html.Label("Unit (Num / Denom)", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '8px'}),
                            html.Div([
                                dcc.Input(
                                    id='input-unit-num', 
                                    type='text', 
                                    placeholder='(e.g., kg)', 
                                    style={'width': '45%', 'padding': '8px', 'borderRadius': '4px', 'border': '1px solid #ccc', 'display': 'inline-block'}
                                ),
                                html.Span(" / ", style={'width': '10%', 'display': 'inline-block', 'textAlign': 'center', 'fontWeight': 'bold', 'fontSize': '18px'}),
                                dcc.Input(
                                    id='input-unit-denom', 
                                    type='text', 
                                    placeholder='(e.g., hr)', 
                                    value='1',
                                    style={'width': '45%', 'padding': '8px', 'borderRadius': '4px', 'border': '1px solid #ccc', 'display': 'inline-block'}
                                ),
                            ], style={'display': 'flex', 'alignItems': 'center'})
                        ], style={'width': '48%', 'display': 'inline-block'}),
                    ]),

                    html.Label("Index Settings", style={'fontWeight': 'bold', 'display': 'block', 'marginTop': '15px', 'marginBottom': '8px'}),
                    dcc.RadioItems(
                        id='input-is-indexed',
                        options=[{'label': ' No (Scalar)', 'value': 'no'}, {'label': ' Yes (Array)', 'value': 'yes'}],
                        value='no',
                        inline=True,
                        style={'marginBottom': '15px'}
                    ),
                    
                    html.Div(id='index-config-area', children=[
                        html.Label("↳ Number of Dimensions (1~5)", style={'fontSize': '14px', 'marginBottom': '5px', 'display': 'block'}),
                        dcc.Input(id='input-num-indices', type='number', value=1, min=1, max=5, style={'width': '80px', 'padding': '5px', 'borderRadius': '4px', 'border': '1px solid #ccc'}),
                        html.Div(id='dynamic-index-inputs', style={'marginTop': '10px', 'padding': '15px', 'backgroundColor': '#fff', 'borderRadius': '8px', 'border': '1px solid #eee'})
                    ], style={'display': 'none', 'marginBottom': '20px'}),

                    html.Div(id='value-input-container', children=[
                        html.Label("Value (Constant)", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '8px'}),
                        dcc.Input(id='input-value', type='number', placeholder='Enter number', style=input_style)
                    ], style={'display': 'none'}),

                    html.Div(id='type-input-container', children=[
                        html.Label("Variable Type", style={'fontWeight': 'bold', 'display': 'block', 'marginBottom': '8px'}),
                        dcc.Dropdown(
                            id='input-var-type',
                            options=[{'label': i, 'value': i} for i in ['Continuous', 'Integer', 'Binary']],
                            value='Continuous',
                            style={'marginBottom': '20px'}
                        )
                    ], style={'display': 'block'}),

                    html.Button("⬇️ Add to Table", id='submit-btn', n_clicks=0, 
                                style={'width': '100%', 'backgroundColor': '#007bff', 'color': 'white', 'padding': '12px', 'border': 'none', 'borderRadius': '6px', 'marginTop': '15px', 'fontWeight': '600', 'fontSize': '16px', 'cursor': 'pointer'})

                ], style=question_style),
                
                html.Div(id='msg-output', style={'marginBottom': '20px', 'textAlign': 'center', 'fontWeight': 'bold', 'minHeight': '24px'}),

                dcc.Tabs(id='sub-tabs', value='tab-var', children=[
                    dcc.Tab(label='📋 Variables List', value='tab-var', style={'fontWeight': '600'}, selected_style={'fontWeight': '600', 'borderTop': '3px solid #28a745'}, children=[html.Div([variable_table], style={'padding': '20px', 'border': '1px solid #dee2e6', 'borderTop': 'none'})]),
                    dcc.Tab(label='🔢 Parameters List', value='tab-param', style={'fontWeight': '600'}, selected_style={'fontWeight': '600', 'borderTop': '3px solid #ffc107'}, children=[html.Div([parameter_table], style={'padding': '20px', 'border': '1px solid #dee2e6', 'borderTop': 'none'})])
                ])

            ])
        ]),

        dcc.Tab(label='STEP 2: Model & Solve', value='view-model', style={'padding': '10px', 'fontWeight': 'bold'}, selected_style={'padding': '10px', 'fontWeight': 'bold', 'borderTop': '3px solid #007bff'}, children=[
            html.Div([
                html.H3("Optimization Modeling", style={'marginTop': '30px', 'marginBottom': '20px'}),
                
                html.Label("🎯 Objective Function", style={'fontWeight': 'bold', 'fontSize': '18px', 'marginBottom': '10px', 'display': 'block'}),
                
                html.Div([
                    dcc.Dropdown(
                        id='objective-type', 
                        options=[{'label': 'Minimize (MIN)', 'value': 'MIN'}, {'label': 'Maximize (MAX)', 'value': 'MAX'}], 
                        value='MIN', 
                        clearable=False,
                        style={'width': '160px'} 
                    ),
                    dcc.Input(
                        id='objective-formula', 
                        type='text', 
                        placeholder='e.g., SUM(Production[i] * Cost[i])', 
                        style={'flex': '1', 'marginLeft': '10px', 'padding': '8px', 'borderRadius': '4px', 'border': '1px solid #ccc'}
                    )
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '30px'}),

                html.Label("🔒 Constraints", style={'fontWeight': 'bold', 'fontSize': '18px', 'marginBottom': '10px', 'display': 'block'}),
                dcc.Textarea(
                    id='constraints-formula',
                    placeholder='Enter one constraint per line.\ne.g., SUM(Production) <= Budget\nProduction[i] >= 10',
                    style={'width': '100%', 'height': 200, 'padding': '15px', 'fontFamily': 'monospace', 'borderRadius': '8px', 'border': '1px solid #ccc', 'lineHeight': '1.5'}
                ),
                
                html.Button("🚀 Run Solver", id='solve-btn', n_clicks=0, 
                            style={'width': '100%', 'marginTop': '30px', 'backgroundColor': '#28a745', 'color': 'white', 'padding': '15px', 'fontSize': '18px', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '8px', 'cursor': 'pointer', 'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'}),
                
                html.Div(id='solver-output', style={'marginTop': '30px', 'padding': '25px', 'border': '1px solid #e9ecef', 'borderRadius': '8px', 'minHeight': '100px', 'backgroundColor': '#f8f9fa'})
            ])
        ])

    ])

], style=app_style)

@app.callback(
    [Output('index-config-area', 'style'),
     Output('value-input-container', 'style'),
     Output('type-input-container', 'style')],
    [Input('input-category', 'value'),
     Input('input-is-indexed', 'value')]
)
def toggle_visibility(category, is_indexed):
    show = {'display': 'block', 'marginBottom': '20px'}
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
            html.Label(f"📌 Range for Index {i+1} (e.g., 1..10 or Seoul,Busan):", style={'fontSize': '13px', 'fontWeight': '500', 'marginBottom': '5px', 'display': 'block'}),
            dcc.Input(id={'type': 'idx-range-input', 'index': i}, type='text', style={'width': '100%', 'padding': '8px', 'borderRadius': '4px', 'border': '1px solid #ccc', 'marginBottom': '10px'})
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
     State('input-unit-num', 'value'),
     State('input-unit-denom', 'value'),
     State('input-is-indexed', 'value'),
     State('input-num-indices', 'value'),
     State({'type': 'idx-range-input', 'index': ALL}, 'value'),
     State('input-value', 'value'),
     State('input-var-type', 'value'),
     State('var-table', 'data'),
     State('param-table', 'data')]
)
def add_row(n_clicks, category, name, u_num, u_denom, is_indexed, num_indices, idx_ranges_list, val, var_type, var_rows, param_rows):
    if n_clicks == 0: return dash.no_update
    if not name: return dash.no_update, dash.no_update, html.Span("❌ Please enter a name!", style={'color': '#dc3545'}), dash.no_update

    final_u_num = u_num if u_num else "-"
    final_u_denom = u_denom if u_denom else "1"

    if is_indexed == 'yes':
        final_num_indices = num_indices
        valid_ranges = [r for r in idx_ranges_list if r]
        final_range_str = ", ".join(valid_ranges)
    else:
        final_num_indices = 0
        final_range_str = ""
        
    new_row = {
        'var_name': name, 
        'unit_num': final_u_num, 
        'unit_denom': final_u_denom,
        'num_indices': final_num_indices, 
        'index_range': final_range_str
    }

    if category == 'param':
        new_row['value'] = val if is_indexed == 'no' else ""
        param_rows.append(new_row)
        return var_rows, param_rows, html.Span(f"✅ Added Parameter '{name}'", style={'color': '#28a745'}), ""
    else:
        new_row['var_type'] = var_type
        var_rows.append(new_row)
        return var_rows, param_rows, html.Span(f"✅ Added Variable '{name}'", style={'color': '#28a745'}), ""

@app.callback(
    Output('solver-output', 'children'),
    Input('solve-btn', 'n_clicks'),
    [State('objective-formula', 'value'),
     State('constraints-formula', 'value')]
)
def run_solver(n_clicks, obj, const):
    if n_clicks == 0: return "Ready. Define data in Step 1, then build model here."
    return html.Div([
        html.H4("⚙️ Solver Initialized...", style={'marginBottom': '15px'}),
        html.P([html.Strong("Objective: "), str(obj)], style={'marginBottom': '10px'}),
        html.P([html.Strong("Constraints: "), "(Engine linkage required)"], style={'marginBottom': '10px'}),
        html.Div("⚠️ UI Only. Connect optimization engine in Phase 3.", style={'color': '#856404', 'backgroundColor': '#fff3cd', 'padding': '10px', 'borderRadius': '4px', 'marginTop': '15px'})
    ])

if __name__ == '__main__':
    app.run_server(debug=True, dev_tools_ui=False)
