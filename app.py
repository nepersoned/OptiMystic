
import dash
from dash import html, dash_table, dcc, Input, Output, State, ALL, callback_context
import json
import solver_engine

external_stylesheets = ['https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, title='OptiMystic Solver', suppress_callback_exceptions=True)
server = app.server

# --- Styles (Restored) ---
app_style = {
    'fontFamily': 'Inter, sans-serif',
    'maxWidth': '1200px', 'margin': 'auto', 'padding': '40px 20px', 'color': '#333'
}

# Card Style (Restored)
card_style = {
    'border': '1px solid #e0e0e0', 'borderRadius': '12px', 'padding': '30px',
    'textAlign': 'center', 'cursor': 'pointer', 'backgroundColor': 'white',
    'boxShadow': '0 8px 16px rgba(0,0,0,0.08)', 'transition': 'transform 0.2s',
    'minHeight': '320px', 'display': 'flex', 'flexDirection': 'column',
    'justifyContent': 'space-between', 'alignItems': 'center', 'gap': '15px'
}

# Input Section Style
question_style = {
    'padding': '25px', 'backgroundColor': '#f8f9fa', 'borderRadius': '12px',
    'marginBottom': '30px', 'border': '1px solid #e9ecef', 'boxShadow': '0 4px 12px rgba(0,0,0,0.05)'
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

# 1. Wizard Input (Default for Custom Mode)
wizard_input_section = html.Div([
    html.H4("1. Data Definition Wizard", style={'marginBottom': '20px'}),
    
    html.Label("Step 1. What is the Role?", style={'fontWeight': 'bold', 'color': '#007bff'}),
    dcc.RadioItems(
        id='input-role',
        options=[{'label': ' Decision Variable (Unknown)', 'value': 'var'}, {'label': ' Parameter (Known Constant)', 'value': 'param'}],
        value='var', labelStyle={'display': 'inline-block', 'marginRight': '20px', 'marginBottom': '15px'}
    ),

    html.Label("Step 2. What is the Shape?", style={'fontWeight': 'bold', 'color': '#28a745'}),
    dcc.RadioItems(
        id='input-shape',
        options=[{'label': ' Scalar', 'value': 'scalar'}, {'label': ' Matrix', 'value': 'matrix'}, {'label': ' List', 'value': 'list'}],
        value='scalar', labelStyle={'display': 'inline-block', 'marginRight': '20px', 'marginBottom': '15px'}
    ),
    
    html.Hr(style={'margin': '20px 0', 'borderTop': '1px dashed #ccc'}),
    html.Label("Name:", style={'fontWeight': 'bold'}),
    dcc.Input(id='input-name', type='text', placeholder="Enter unique name...", style=input_style),

    # Matrix Config
    html.Div(id='matrix-config-area', children=[
        html.Div([html.Div([html.Label("Row Labels:"), dcc.Input(id='matrix-rows', type='text', style=input_style)], style={'width':'48%'}), 
                  html.Div([html.Label("Col Labels:"), dcc.Input(id='matrix-cols', type='text', style=input_style)], style={'width':'48%'})], style={'display':'flex', 'gap':'4%'}),
        html.Button("Generate Grid", id='btn-gen-matrix', n_clicks=0, style={'marginTop': '5px', 'padding': '8px', 'cursor': 'pointer'}),
        html.Div(style={'marginTop': '15px'}, children=[dash_table.DataTable(id='matrix-data-table', columns=[{'name':'No Data','id':'dummy'}], data=[], editable=True, style_table={'display':'none'})])
    ], style={'display':'none', 'padding': '15px', 'backgroundColor': '#e9ecef', 'borderRadius': '8px', 'marginBottom': '15px'}),

    # List Config
    html.Div(id='list-config-area', children=[
        html.Label("Columns (comma separated):"), dcc.Input(id='list-cols', type='text', style=input_style),
        html.Button("Initialize List", id='btn-init-list', n_clicks=0, style={'marginTop': '5px', 'padding': '8px', 'cursor': 'pointer'}),
        html.Div(id='list-input-container', style={'marginTop': '15px', 'display': 'none'}, children=[
            dash_table.DataTable(id='list-data-table', columns=[{'name':'Col1','id':'col1'}], data=[], editable=True, row_deletable=True),
            html.Button("+ Add Row", id='btn-add-list-row', n_clicks=0, style={'marginTop': '10px', 'width': '100%'})
        ])
    ], style={'display':'none', 'padding': '15px', 'backgroundColor': '#e3f2fd', 'borderRadius': '8px', 'marginBottom': '15px'}),

    # Value & Type
    html.Div(id='val-input-box', style={'display':'none'}, children=[html.Label("Value:"), dcc.Input(id='input-value', type='number', style=input_style)]),
    html.Div(id='type-input-box', style={'display':'block'}, children=[
        html.Label("Type:", style={'fontWeight':'bold','color':'#d63384'}), 
        dcc.Dropdown(id='input-var-type', options=[{'label':'Continuous','value':'Continuous'},{'label':'Integer','value':'Integer'}], value='Continuous', style={'marginBottom':'10px'})
    ]),

    html.Button('Add to Table', id='add-btn', n_clicks=0, style={'width': '100%', 'padding': '12px', 'backgroundColor': '#4a4e69', 'color': 'white', 'border': 'none', 'borderRadius': '8px', 'cursor': 'pointer'}),
    html.Div(id='add-msg', style={'marginTop': '10px'})
], style=question_style)

# 2. Production Mix Custom UI (Phase 6 New!)
prod_mix_input_section = html.Div([
    html.H4("🏭 Production Mix Setup", style={'marginBottom': '20px', 'color': '#4a4e69'}),
    html.P("Define your products and resource usage below. No formulas needed!", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '20px'}),
    
    html.Div([
        html.H5("1. Define Products & Profit", style={'color': '#007bff'}),
        dash_table.DataTable(
            id='pm-products-table',
            columns=[
                {'name': 'Product Name', 'id': 'Product', 'editable': True},
                {'name': 'Profit ($)', 'id': 'Profit', 'type': 'numeric', 'editable': True}
            ],
            data=[{'Product': 'P1', 'Profit': 100}, {'Product': 'P2', 'Profit': 150}],
            row_deletable=True,
            editable=True,
            style_header=table_header_style, style_cell=table_cell_style
        ),
        html.Button("+ Add Product", id='pm-add-prod-btn', n_clicks=0, style={'marginTop': '10px', 'padding': '5px 10px', 'cursor': 'pointer', 'backgroundColor': '#007bff', 'color': 'white', 'border': 'none', 'borderRadius': '4px'})
    ], style={'marginBottom': '30px', 'padding': '20px', 'border': '1px solid #cce5ff', 'borderRadius': '12px', 'backgroundColor': '#f8f9fa'}),

    html.Div([
        html.H5("2. Resource Usage", style={'color': '#28a745'}),
        html.P("Enter resource consumption per unit.", style={'fontSize': '13px'}),
        html.Div(id='pm-resource-matrix-container', style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '8px', 'border': '1px solid #ddd'})
    ], style={'padding': '20px', 'border': '1px solid #d4edda', 'borderRadius': '12px', 'backgroundColor': '#f8f9fa'})

], style=question_style)

# --- Modeling Section (Step 2) ---
modeling_section = html.Div([
    html.H4("⚙️ Solver Engine", style={'marginBottom': '20px', 'color': '#4a4e69'}),
    
    html.Div([
        html.Label("1. Objective Goal:", style={'fontWeight': 'bold', 'color': '#007bff'}),
        dcc.RadioItems(id='solver-sense', options=[{'label': ' Minimize', 'value': 'minimize'}, {'label': ' Maximize', 'value': 'maximize'}], value='minimize', labelStyle={'display': 'inline-block', 'marginRight': '20px'}),
        dcc.Textarea(id='solver-objective', placeholder="e.g. 5*P1 + 9*P2...", style={'width': '100%', 'height': '60px', 'marginTop': '10px', 'borderRadius': '4px', 'border': '1px solid #ccc'}),
        
        html.Label("2. Constraints:", style={'fontWeight': 'bold', 'color': '#d63384', 'marginTop': '20px'}),
        dcc.Textarea(id='solver-constraints', placeholder="e.g. 3*P1 <= 100...", style={'width': '100%', 'height': '150px', 'borderRadius': '4px', 'border': '1px solid #ccc'}),
        
        html.Button("🚀 Run Optimization", id='btn-solve', n_clicks=0, 
                    style={'width': '100%', 'marginTop':'20px', 'padding': '15px', 'backgroundColor': '#28a745', 'color': 'white', 'border': 'none', 'borderRadius': '8px', 'fontSize': '18px', 'cursor': 'pointer', 'fontWeight': 'bold'})
    ], style=question_style)
])

# --- Dashboard Section (Step 3: Restored) ---
dashboard_section = html.Div([
    html.H4("📊 Optimization Dashboard", style={'marginBottom': '20px', 'color': '#4a4e69'}),
    
    # Status & Objective Cards (Restored)
    html.Div([
        html.Div([
            html.H6("Solver Status", style={'color': '#6c757d', 'fontSize': '14px', 'marginBottom': '5px'}),
            html.H2(id='res-status', children="-", style={'margin': 0, 'fontWeight': 'bold', 'color': '#333'})
        ], style={'flex': '1', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'textAlign': 'center', 'border': '1px solid #e9ecef'}),
        
        html.Div([
            html.H6("Objective Value", style={'color': '#6c757d', 'fontSize': '14px', 'marginBottom': '5px'}),
            html.H2(id='res-objective', children="-", style={'margin': 0, 'fontWeight': 'bold', 'color': '#007bff'})
        ], style={'flex': '1', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '12px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'textAlign': 'center', 'border': '1px solid #e9ecef'}),
    ], style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}),

    # Result Tables (Restored)
    html.Div(id='result-dashboard', style={'display': 'none'}, children=[
        html.H5("🧩 Decision Variables", style={'marginBottom': '15px'}),
        dash_table.DataTable(
            id='res-table', 
            columns=[{'name': 'Variable', 'id': 'Variable'}, {'name': 'Optimal Value', 'id': 'Value'}], 
            data=[],
            style_header=table_header_style, 
            style_cell=table_cell_style,
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}]
        ),
        
        html.H5("🔍 Sensitivity Analysis (Constraints)", style={'marginTop': '30px', 'marginBottom': '15px', 'color': '#d63384'}),
        dash_table.DataTable(
            id='res-constraints-table', 
            columns=[{'name': 'Constraint ID', 'id': 'Constraint'}, {'name': 'Shadow Price', 'id': 'Shadow Price'}, {'name': 'Slack (Remaining)', 'id': 'Slack (Remaining)'}], 
            data=[],
            style_header={'backgroundColor': '#fff0f6', 'fontWeight': 'bold', 'border': '1px solid #dee2e6', 'textAlign': 'left', 'padding': '10px'},
            style_cell=table_cell_style
        )
    ]),
    
    html.Div(id='solver-error-msg', style={'color': '#dc3545', 'marginTop': '20px', 'fontWeight': 'bold', 'whiteSpace': 'pre-wrap'})
], style={'padding': '30px', 'backgroundColor': '#f8f9fa', 'borderRadius': '12px'})

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
    
    # Show Specific UI for Production Mix
    if mode == 'prod_mix':
        input_content = prod_mix_input_section
    else:
        # Default Wizard for others
        input_content = html.Div([
            wizard_input_section,
            html.H4("📊 Defined Data List", style={'marginTop': '30px'}),
            dash_table.DataTable(id='var-table', columns=[{'name': i, 'id': i} for i in ['Name', 'Shape', 'Type', 'Preview']], data=[], style_header=table_header_style, style_cell=table_cell_style),
            dash_table.DataTable(id='param-table', columns=[{'name': i, 'id': i} for i in ['Name', 'Shape', 'Value/Preview']], data=[], style_header=table_header_style, style_cell=table_cell_style),
        ], style={'padding': '20px'})

    return html.Div([
        dcc.Store(id='all-data-store', data={'variables': [], 'parameters': []}),
        html.Div([html.Span(f"Selected Mode: {title}", style={'backgroundColor': '#e2e6ea', 'padding': '5px 10px', 'borderRadius': '15px', 'fontSize': '14px', 'fontWeight': '600'})], style={'marginBottom': '20px'}),
        dcc.Tabs([
            dcc.Tab(label='STEP 1: Data Input', children=[input_content]),
            dcc.Tab(label='STEP 2: Solver', children=[modeling_section]),
            dcc.Tab(label='STEP 3: Dashboard', children=[dashboard_section])
        ])
    ], key=mode)

# --- Main Layout ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div([
        html.H2("🧙‍♂️ OptiMystic Solver", style={'margin': 0, 'color': '#4a4e69'}),
        html.Button("🏠 Home", id='btn-home', style={'padding': '5px 10px', 'cursor': 'pointer', 'border': 'none', 'background': 'transparent', 'fontSize': '16px'})
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '30px', 'borderBottom': '1px solid #eee', 'paddingBottom': '15px'}),
    html.Div(id='page-content')
], style=app_style)

# --- Callbacks ---

@app.callback(
    Output('url', 'pathname'),
    [Input({'type': 'tmpl-btn', 'index': ALL}, 'n_clicks'), Input('btn-home', 'n_clicks')],
    [State('url', 'pathname')]
)
def change_url(tmpl_clicks, home_click, current_path):
    ctx = callback_context
    if not ctx.triggered: return dash.no_update
    btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if btn_id == 'btn-home':
        return "/home"
        
    if 'tmpl-btn' in btn_id:
        try:
            mode = json.loads(btn_id)['index']
            return f"/{mode}"
        except: return dash.no_update
    return dash.no_update

@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def render_page_content(pathname):
    # Enhanced Guard Clause for Home Redirection
    if pathname in [None, '/', '/home', '']: return render_landing_page()
    try:
        mode = pathname.strip('/')
        return render_workspace(mode)
    except: return render_landing_page()

# --- Wizard Logic ---
@app.callback([Output('matrix-config-area', 'style'), Output('list-config-area', 'style'), Output('val-input-box', 'style'), Output('type-input-box', 'style')], [Input('input-role', 'value'), Input('input-shape', 'value')])
def toggle_inputs(role, shape):
    matrix_style = {'display': 'block', 'padding': '15px', 'backgroundColor': '#e9ecef', 'borderRadius': '8px', 'marginBottom': '15px'} if shape == 'matrix' else {'display': 'none'}
    list_style = {'display': 'block', 'padding': '15px', 'backgroundColor': '#e3f2fd', 'borderRadius': '8px', 'marginBottom': '15px'} if shape == 'list' else {'display': 'none'}
    val_style = {'display': 'block', 'marginBottom': '15px'} if role == 'param' and shape == 'scalar' else {'display': 'none'}
    type_style = {'display': 'block', 'marginBottom': '15px'} if role == 'var' else {'display': 'none'}
    return matrix_style, list_style, val_style, type_style

@app.callback([Output('matrix-data-table', 'data'), Output('matrix-data-table', 'columns'), Output('matrix-data-table', 'style_table')], Input('btn-gen-matrix', 'n_clicks'), [State('matrix-rows', 'value'), State('matrix-cols', 'value')])
def generate_matrix(n, r_str, c_str):
    if n==0: return [], [{'name':'No Data','id':'dummy'}], {'display':'none'}
    rows = [r.strip() for r in r_str.split(',')] if r_str else ['R1']
    cols = [c.strip() for c in c_str.split(',')] if c_str else ['C1']
    return [{'row_label': r, **{c: 0 for c in cols}} for r in rows], [{'name':'Label','id':'row_label','editable':False}]+[{'name':c,'id':c,'type':'numeric'} for c in cols], {'overflowX':'auto','minWidth':'100%','display':'block'}

@app.callback([Output('list-data-table', 'data'), Output('list-data-table', 'columns'), Output('list-input-container', 'style')], [Input('btn-init-list', 'n_clicks'), Input('btn-add-list-row', 'n_clicks')], [State('list-cols', 'value'), State('list-data-table', 'data'), State('list-data-table', 'columns')])
def manage_list(ic, ac, cs, data, cols):
    ctx = callback_context
    if not ctx.triggered: return [], [{'name':'Col1','id':'col1'}], {'display':'none'}
    bid = ctx.triggered[0]['prop_id'].split('.')[0]
    if bid == 'btn-init-list':
        c_list = [c.strip() for c in cs.split(',')] if cs else ['Item']
        return [{c: 0 for c in c_list}], [{'name': c, 'id': c, 'type': 'numeric'} for c in c_list], {'marginTop':'15px','display':'block'}
    if bid == 'btn-add-list-row' and cols:
        data.append({c['id']: 0 for c in cols})
        return data, cols, {'marginTop':'15px','display':'block'}
    return [], [], {'display':'none'}

@app.callback([Output('var-table', 'data'), Output('param-table', 'data'), Output('all-data-store', 'data'), Output('add-msg', 'children'), Output('input-name', 'value')], Input('add-btn', 'n_clicks'), [State('input-role', 'value'), State('input-shape', 'value'), State('input-name', 'value'), State('input-value', 'value'), State('input-var-type', 'value'), State('matrix-data-table', 'data'), State('list-data-table', 'data'), State('var-table', 'data'), State('param-table', 'data'), State('all-data-store', 'data')])
def add_data(n, role, shape, name, val, vtype, m_data, l_data, v_rows, p_rows, store):
    if n==0: return [], [], store, "", ""
    if not name: return dash.no_update, dash.no_update, dash.no_update, html.Span("Name required!", style={'color':'red'}), dash.no_update
    if v_rows is None: v_rows=[]
    if p_rows is None: p_rows=[]
    if store is None: store={'variables':[],'parameters':[]}
    
    r_data = val if shape=='scalar' and role=='param' else (m_data if shape=='matrix' else (l_data if shape=='list' else None))
    prev = str(val) if shape=='scalar' and role=='param' else ("-" if role=='var' else f"{shape}")
    
    # Update UI Preview
    if role == 'var':
        v_rows.append({'Name': name, 'Shape': shape, 'Type': vtype, 'Preview': '-'})
        store['variables'].append({'name': name, 'shape': shape, 'type': vtype, 'data': r_data})
        msg = html.Span(f"✅ Variable '{name}' added!", style={'color':'blue'})
    else:
        p_rows.append({'Name': name, 'Shape': shape, 'Value/Preview': prev})
        store['parameters'].append({'name': name, 'shape': shape, 'data': r_data})
        msg = html.Span(f"✅ Parameter '{name}' added!", style={'color':'green'})
    return v_rows, p_rows, store, msg, ""

# --- Solver Run Logic ---
@app.callback([Output('result-dashboard', 'style'), Output('res-status', 'children'), Output('res-status', 'style'), Output('res-objective', 'children'), Output('res-table', 'data'), Output('res-constraints-table', 'data'), Output('solver-error-msg', 'children')], Input('btn-solve', 'n_clicks'), [State('solver-sense', 'value'), State('solver-objective', 'value'), State('solver-constraints', 'value'), State('all-data-store', 'data')])
def run_solver(n, sense, obj, const, store):
    if n==0 or not obj: return {'display':'none'}, "-", {}, "-", [], [], ""
    res = solver_engine.solve_model(store, sense, obj, const)
    if res.get('status') == 'Error': return {'display':'none'}, "Error", {'color':'#dc3545'}, "-", [], [], f"System Error:\n{res.get('error_msg')}"
    
    # Restore Style & Formatting
    status_style = {'color': '#28a745'} if res['status'] == 'Optimal' else {'color': '#ffc107'}
    formatted_obj = f"{res['objective']:,.2f}"
    
    return {'display':'block'}, res['status'], status_style, formatted_obj, res['variables'], res['constraints'], ""

if __name__ == '__main__':
    app.run_server(debug=True)
