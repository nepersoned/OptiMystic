import dash
from dash import html, dash_table, dcc, Input, Output, State, ALL, callback_context
import json

external_stylesheets = ['https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, title='OptiMystic Solver', suppress_callback_exceptions=True)
server = app.server

app_style = {
    'fontFamily': 'Inter, sans-serif',
    'maxWidth': '1200px',
    'margin': 'auto',
    'padding': '40px 20px',
    'color': '#333'
}

card_style = {
    'border': '1px solid #e0e0e0', 'borderRadius': '12px', 'padding': '30px',
    'textAlign': 'center', 'cursor': 'pointer', 'backgroundColor': 'white',
    'boxShadow': '0 8px 16px rgba(0,0,0,0.08)', 'transition': 'transform 0.2s',
    'minHeight': '320px', 'display': 'flex', 'flexDirection': 'column',
    'justifyContent': 'space-between', 'alignItems': 'center', 'gap': '15px'
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
    'width': '100%', 'padding': '8px', 'borderRadius': '4px',
    'border': '1px solid #ccc', 'marginBottom': '10px'
}

table_header_style = {
    'backgroundColor': '#f1f3f5', 'fontWeight': '600',
    'border': '1px solid #dee2e6', 'textAlign': 'left', 'padding': '10px'
}

table_cell_style = {
    'padding': '10px', 'border': '1px solid #dee2e6',
    'fontSize': '14px', 'fontFamily': 'Inter, sans-serif'
}

TEMPLATE_GALLERY = [
    {"id": "cutting", "icon": "✂️", "title": "Cutting Stock", "desc": "Minimize material waste (1D packing) for pipes, wood, or coils."},
    {"id": "packing", "icon": "📦", "title": "Bin Packing", "desc": "Maximize truck or container loading efficiency (Knapsack Problem)."},
    {"id": "blending", "icon": "🧪", "title": "Blending Optimization", "desc": "Find the optimal recipe/mix to minimize cost while meeting quality."},
    {"id": "prod_mix", "icon": "🏭", "title": "Production Mix", "desc": "Maximize profit by determining optimal production quantities."},
    {"id": "schedule", "icon": "📅", "title": "Shift Scheduling", "desc": "Automate workforce rostering respecting legal constraints."},
    {"id": "transport", "icon": "🚚", "title": "Transportation", "desc": "Minimize logistics costs from sources to destinations."},
    {"id": "custom", "icon": "🔮", "title": "Custom Mode", "desc": "Build your own model from scratch using the Wizard."}
]

# --- UI Components ---

wizard_input_section = html.Div([
    html.H4("1. Data Definition Wizard", style={'marginBottom': '20px'}),
    
    # [1] Role Selection
    html.Label("Step 1. What is the Role?", style={'fontWeight': 'bold', 'color': '#007bff'}),
    dcc.RadioItems(
        id='input-role',
        options=[
            {'label': ' Decision Variable (Unknown)', 'value': 'var'},
            {'label': ' Parameter (Known Constant)', 'value': 'param'}
        ],
        value='var',
        labelStyle={'display': 'inline-block', 'marginRight': '20px', 'marginBottom': '15px'}
    ),

    # [2] Shape Selection
    html.Label("Step 2. What is the Shape?", style={'fontWeight': 'bold', 'color': '#28a745'}),
    dcc.RadioItems(
        id='input-shape',
        options=[
            {'label': ' Scalar (Single Value)', 'value': 'scalar'},
            {'label': ' Matrix / Grid (2D Table)', 'value': 'matrix'}
        ],
        value='scalar',
        labelStyle={'display': 'inline-block', 'marginRight': '20px', 'marginBottom': '15px'}
    ),
    
    html.Hr(style={'margin': '20px 0', 'borderTop': '1px dashed #ccc'}),

    # Common Input: Name
    html.Label("Name (e.g., Production_Qty, Transport_Cost):", style={'fontWeight': 'bold'}),
    dcc.Input(id='input-name', type='text', placeholder="Enter unique name...", style=input_style),

    html.Div(id='matrix-config-area', children=[
        html.Label("Matrix Configuration:", style={'fontWeight': 'bold', 'marginTop': '10px'}),
        html.Div([
            html.Div([
                html.Label("Row Labels (comma separated):", style={'fontSize': '13px'}),
                dcc.Input(id='matrix-rows', type='text', placeholder="e.g. Factory_A, Factory_B", style=input_style)
            ], style={'width': '48%', 'marginRight': '4%'}),
            html.Div([
                html.Label("Column Labels (comma separated):", style={'fontSize': '13px'}),
                dcc.Input(id='matrix-cols', type='text', placeholder="e.g. Warehouse_1, Warehouse_2", style=input_style)
            ], style={'width': '48%'}),
        ], style={'display': 'flex'}),
        
        html.Button("Generate Grid", id='btn-gen-matrix', n_clicks=0, 
                   style={'marginTop': '5px', 'padding': '8px 15px', 'backgroundColor': '#6c757d', 'color': 'white', 'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer'}),
        
        html.Div(id='matrix-input-container', style={'marginTop': '15px'}, children=[
             dash_table.DataTable(
                id='matrix-data-table',
                columns=[{'name': 'No Data', 'id': 'dummy'}], 
                data=[], editable=True,
                style_table={'display': 'none'}, 
                style_cell={'textAlign': 'center', 'minWidth': '80px'},
                style_header={'backgroundColor': '#adb5bd', 'color': 'white', 'fontWeight': 'bold'}
            )
        ])
    ], style={'display': 'none', 'padding': '15px', 'backgroundColor': '#e9ecef', 'borderRadius': '8px', 'marginBottom': '15px'}),

    html.Div(id='val-input-box', children=[
        html.Label("Parameter Value (Numeric):", style={'fontWeight': 'bold'}),
        dcc.Input(id='input-value', type='number', placeholder="Enter value", style=input_style)
    ], style={'display': 'none'}),

    html.Div(id='type-input-box', children=[
        html.Label("Variable Type (Constraints):", style={'fontWeight': 'bold', 'color': '#d63384'}),
        dcc.Dropdown(
            id='input-var-type',
            options=[
                {'label': 'Continuous (Real Number)', 'value': 'Continuous'},
                {'label': 'Integer (Whole Number)', 'value': 'Integer'},
                {'label': 'Binary (0 or 1)', 'value': 'Binary'}
            ],
            value='Continuous', style={'marginBottom': '10px'}
        )
    ], style={'display': 'block'})

], style=question_style)

modeling_section = html.Div([
    html.H4("Optimization Model (Preview)", style={'marginBottom': '20px'}),
    html.Div("Phase 4 (Solver Engine) will be connected here.", style={'color': '#888', 'fontStyle': 'italic'})
])

# --- Helper Functions ---
def render_landing_page():
    cards = []
    for t in TEMPLATE_GALLERY:
        card = html.Div([
            html.Div(t['icon'], style={'fontSize': '40px', 'marginBottom': '10px'}),
            html.H3(t['title'], style={'fontSize': '18px', 'marginBottom': '8px', 'color': '#333'}),
            html.P(t['desc'], style={'fontSize': '14px', 'color': '#666', 'lineHeight': '1.4'}),
            html.Button("Select", id={'type': 'tmpl-btn', 'index': t['id']}, style={'marginTop': '15px', 'padding': '8px 16px', 'backgroundColor': '#4a4e69', 'color': 'white', 'border': 'none', 'borderRadius': '6px', 'cursor': 'pointer'})
        ], style=card_style)
        cards.append(card)
    return html.Div([
        html.H1("Which optimization problem do you want to solve?", style={'textAlign': 'center', 'marginBottom': '40px', 'color': '#222'}),
        html.Div(cards, style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(280px, 1fr))', 'gap': '20px'})
    ])

def render_workspace(mode):
    mode_info = next((item for item in TEMPLATE_GALLERY if item["id"] == mode), None)
    title = mode_info['title'] if mode_info else "Custom Mode"
    return html.Div([
        html.Div([html.Span(f"Selected Mode: {title}", style={'backgroundColor': '#e2e6ea', 'padding': '5px 10px', 'borderRadius': '15px', 'fontSize': '14px', 'fontWeight': '600'})], style={'marginBottom': '20px'}),
        dcc.Tabs([
            dcc.Tab(label='STEP 1: Data Input', children=[
                html.Div([
                    wizard_input_section,
                    html.Button('Add to Table', id='add-btn', n_clicks=0, style={'width': '100%', 'padding': '12px', 'backgroundColor': '#4a4e69', 'color': 'white', 'border': 'none', 'borderRadius': '8px', 'cursor': 'pointer', 'fontSize': '16px'}),
                    html.Div(id='add-msg', style={'marginTop': '10px'}),
                    
                    html.H4("📊 Defined Data List", style={'marginTop': '30px'}),
                    # Variable Table
                    html.H5("Decision Variables", style={'color': '#007bff'}),
                    dash_table.DataTable(id='var-table', columns=[{'name': i, 'id': i} for i in ['Name', 'Shape', 'Type', 'Preview']], data=[], style_header=table_header_style, style_cell=table_cell_style),
                    
                    # Parameter Table
                    html.H5("Parameters", style={'color': '#28a745', 'marginTop': '20px'}),
                    dash_table.DataTable(id='param-table', columns=[{'name': i, 'id': i} for i in ['Name', 'Shape', 'Value/Preview']], data=[], style_header=table_header_style, style_cell=table_cell_style),
                ], style={'padding': '20px'})
            ]),
            dcc.Tab(label='STEP 2: Solver', children=[modeling_section])
        ])
    ])

# --- Main Layout ---
app.layout = html.Div([
    dcc.Store(id='current-mode', data='home'),
    html.Div([
        html.H2("🧙‍♂️ OptiMystic Solver", style={'margin': 0, 'color': '#4a4e69'}),
        html.Button("🏠 Home", id='btn-home', style={'padding': '5px 10px', 'cursor': 'pointer', 'border': 'none', 'background': 'transparent'})
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '30px', 'borderBottom': '1px solid #eee', 'paddingBottom': '15px'}),
    html.Div(id='page-content')
], style=app_style)

# --- Callbacks ---

@app.callback(
    [Output('current-mode', 'data'), Output('page-content', 'children')],
    [Input({'type': 'tmpl-btn', 'index': ALL}, 'n_clicks'), Input('btn-home', 'n_clicks')],
    [State('current-mode', 'data')]
)
def navigate(tmpl_clicks, home_click, current_mode):
    ctx = callback_context
    if not ctx.triggered: return 'home', render_landing_page()
    btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if btn_id == 'btn-home': return 'home', render_landing_page()
    if 'tmpl-btn' in btn_id:
        import json
        try:
            mode = json.loads(btn_id)['index']
            return mode, render_workspace(mode)
        except: return 'home', render_landing_page()
    return 'home', render_landing_page()

# [Logic] Visibility Control (Corrected for Type Input)
@app.callback(
    [Output('matrix-config-area', 'style'),
     Output('val-input-box', 'style'),
     Output('type-input-box', 'style')],
    [Input('input-role', 'value'),
     Input('input-shape', 'value')]
)
def toggle_inputs(role, shape):
    # 1. Matrix Area: Show only if Shape == Matrix
    if shape == 'matrix':
        matrix_style = {'display': 'block', 'padding': '15px', 'backgroundColor': '#e9ecef', 'borderRadius': '8px', 'marginBottom': '15px'}
    else:
        matrix_style = {'display': 'none'}

    # 2. Value Input: Show only if Role == Param AND Shape == Scalar
    if role == 'param' and shape == 'scalar':
        val_style = {'display': 'block'}
    else:
        val_style = {'display': 'none'}

    # 3. Type Input: Show if Role == Variable (Regardless of Shape!)
    if role == 'var':
        type_style = {'display': 'block'}
    else:
        type_style = {'display': 'none'}

    return matrix_style, val_style, type_style

# [Logic] Generate Matrix
@app.callback(
    [Output('matrix-data-table', 'data'), Output('matrix-data-table', 'columns'), Output('matrix-data-table', 'style_table')],
    Input('btn-gen-matrix', 'n_clicks'),
    [State('matrix-rows', 'value'), State('matrix-cols', 'value')]
)
def generate_matrix(n_clicks, row_str, col_str):
    if n_clicks == 0: return [], [{'name': 'No Data', 'id': 'dummy'}], {'display': 'none'}
    
    rows = [r.strip() for r in row_str.split(',')] if row_str else ['Row1', 'Row2']
    cols = [c.strip() for c in col_str.split(',')] if col_str else ['Col1', 'Col2']
    
    columns = [{'name': 'Label', 'id': 'row_label', 'editable': False}] + [{'name': c, 'id': c, 'type': 'numeric'} for c in cols]
    data = [{'row_label': r, **{c: 0 for c in cols}} for r in rows]
    
    return data, columns, {'overflowX': 'auto', 'minWidth': '100%', 'display': 'block'}

# [Logic] Add Data
@app.callback(
    [Output('var-table', 'data'), Output('param-table', 'data'),
     Output('add-msg', 'children'), Output('input-name', 'value')],
    Input('add-btn', 'n_clicks'),
    [State('input-role', 'value'), State('input-shape', 'value'), State('input-name', 'value'),
     State('input-value', 'value'), State('input-var-type', 'value'),
     State('matrix-data-table', 'data'), State('var-table', 'data'), State('param-table', 'data')]
)
def add_data_integrated(n_clicks, role, shape, name, val, var_type, matrix_data, var_rows, param_rows):
    if n_clicks == 0: return [], [], "", ""
    if not name: return dash.no_update, dash.no_update, html.Span("❌ Name is required!", style={'color': 'red'}), dash.no_update

    if var_rows is None: var_rows = []
    if param_rows is None: param_rows = []

    # 1. Prepare Data
    if shape == 'scalar':
        preview = str(val) if role == 'param' else "-"
        shape_desc = "Scalar"
    else:
        if not matrix_data: return dash.no_update, dash.no_update, html.Span("❌ Generate matrix first!", style={'color': 'red'}), dash.no_update
        rows = len(matrix_data)
        cols = len(matrix_data[0]) - 1 if rows > 0 else 0
        preview = f"Grid ({rows}x{cols})"
        shape_desc = f"Matrix ({rows}x{cols})"

    new_row = {'Name': name, 'Shape': shape_desc}

    # 2. Add to Table
    if role == 'var':
        new_row['Type'] = var_type
        new_row['Preview'] = "-"
        var_rows.append(new_row)
        msg = html.Span(f"✅ Variable '{name}' ({var_type}) added!", style={'color': 'blue'})
    else:
        new_row['Value/Preview'] = preview
        param_rows.append(new_row)
        msg = html.Span(f"✅ Parameter '{name}' added!", style={'color': 'green'})

    return var_rows, param_rows, msg, ""

if __name__ == '__main__':
    app.run_server(debug=True)
