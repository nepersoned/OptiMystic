import dash
from dash import html, dash_table, dcc, Input, Output, State, ALL, callback_context

# ------------------------------------------------------------------------------
# 1. Styles & Assets
# ------------------------------------------------------------------------------
external_stylesheets = ['https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, title='OptiMystic Solver')
server = app.server

app_style = {
    'fontFamily': 'Inter, sans-serif',
    'maxWidth': '1000px',
    'margin': 'auto',
    'padding': '40px 20px',
    'color': '#333'
}

card_style = {
    'border': '1px solid #e0e0e0', 'borderRadius': '12px', 'padding': '20px',
    'textAlign': 'center', 'cursor': 'pointer', 'backgroundColor': 'white',
    'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'transition': 'transform 0.2s',
    'height': '100%', 'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center'
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

# ------------------------------------------------------------------------------
# 2. Data & Templates (English)
# ------------------------------------------------------------------------------
TEMPLATE_GALLERY = [
    {"id": "cutting", "icon": "✂️", "title": "Cutting Stock", "desc": "Minimize material waste (1D packing) for pipes, wood, or coils."},
    {"id": "packing", "icon": "📦", "title": "Bin Packing", "desc": "Maximize truck or container loading efficiency (Knapsack Problem)."},
    {"id": "blending", "icon": "🧪", "title": "Blending Optimization", "desc": "Find the optimal recipe/mix to minimize cost while meeting quality."},
    {"id": "prod_mix", "icon": "🏭", "title": "Production Mix", "desc": "Maximize profit by determining optimal production quantities."},
    {"id": "schedule", "icon": "📅", "title": "Shift Scheduling", "desc": "Automate workforce rostering respecting legal constraints."},
    {"id": "transport", "icon": "🚚", "title": "Transportation", "desc": "Minimize logistics costs from sources to destinations."},
    {"id": "custom", "icon": "🔮", "title": "Custom Mode", "desc": "Build your own model from scratch using the Wizard."}
]

# ------------------------------------------------------------------------------
# 3. UI Components (Wizard Parts)
# ------------------------------------------------------------------------------

# 3-1. Input Section (Wizard Form)
wizard_input_section = html.Div([
    html.H4("1. Data Definition Wizard", style={'marginBottom': '20px'}),
    
    # Category Selection
    html.Label("What type of data is this?", style={'fontWeight': 'bold'}),
    dcc.RadioItems(
        id='input-category',
        options=[
            {'label': ' Decision Variable (Unknown to solve)', 'value': 'var'},
            {'label': ' Parameter (Known constant)', 'value': 'param'}
        ],
        value='var',
        labelStyle={'display': 'block', 'marginBottom': '10px'}
    ),
    html.Br(),

    # Name Input
    html.Label("Name (e.g., Production_Qty, Cost):", style={'fontWeight': 'bold'}),
    dcc.Input(id='input-name', type='text', placeholder="Enter name...", style=input_style),

    # Unit Input
    html.Label("Unit (Optional):", style={'fontWeight': 'bold', 'marginTop': '10px'}),
    html.Div([
        dcc.Input(id='input-unit-num', type='text', placeholder="Numerator (e.g. km)", style={'width': '48%', 'marginRight': '4%'}),
        dcc.Input(id='input-unit-denom', type='text', placeholder="Denominator (e.g. hour)", style={'width': '48%'})
    ], style={'display': 'flex', 'marginBottom': '15px'}),

    # Index Configuration
    html.Label("Is this data indexed (Sets)?", style={'fontWeight': 'bold'}),
    dcc.RadioItems(
        id='input-is-indexed',
        options=[{'label': ' No (Scalar)', 'value': 'no'}, {'label': ' Yes (Matrix/Vector)', 'value': 'yes'}],
        value='no',
        labelStyle={'display': 'inline-block', 'marginRight': '20px'}
    ),
    
    # Dynamic Index Inputs (Hidden by default)
    html.Div(id='index-config-area', children=[
        html.Label("Number of Indices:", style={'marginTop': '10px'}),
        dcc.Input(id='input-num-indices', type='number', min=1, max=5, step=1, value=1, style=input_style),
        html.Div(id='dynamic-index-inputs')
    ], style={'display': 'none'}),

    # Value Input (Only for Parameters)
    html.Div(id='value-input-container', children=[
        html.Label("Value (Numeric):", style={'fontWeight': 'bold', 'marginTop': '10px'}),
        dcc.Input(id='input-value', type='number', placeholder="Enter constant value", style=input_style)
    ], style={'display': 'none'}),

    # Type Input (Only for Variables)
    html.Div(id='type-input-container', children=[
        html.Label("Variable Type:", style={'fontWeight': 'bold', 'marginTop': '10px'}),
        dcc.Dropdown(
            id='input-var-type',
            options=[
                {'label': 'Continuous (Real Number)', 'value': 'Continuous'},
                {'label': 'Integer (Whole Number)', 'value': 'Integer'},
                {'label': 'Binary (0 or 1)', 'value': 'Binary'}
            ],
            value='Continuous',
            style={'marginBottom': '10px'}
        )
    ], style={'display': 'block'})

], style=question_style)

# 3-2. Modeling Section (Step 2)
modeling_section = html.Div([
    html.H4("Define Optimization Model", style={'marginBottom': '20px'}),
    
    html.Label("Objective Function (Minimize/Maximize):", style={'fontWeight': 'bold'}),
    dcc.Textarea(id='objective-formula', placeholder="e.g., maximize 3*x + 5*y", style={'width': '100%', 'height': '80px', 'marginBottom': '20px'}),
    
    html.Label("Constraints:", style={'fontWeight': 'bold'}),
    dcc.Textarea(id='constraints-formula', placeholder="e.g.,\nx + y <= 10\nx >= 0", style={'width': '100%', 'height': '150px', 'marginBottom': '20px'}),

    html.Button("Run Solver 🚀", id='solve-btn', n_clicks=0, 
                style={'width': '100%', 'padding': '15px', 'backgroundColor': '#28a745', 'color': 'white', 'border': 'none', 'borderRadius': '8px', 'fontSize': '18px', 'cursor': 'pointer'}),
    
    html.Div(id='solver-output', style={'marginTop': '30px', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px', 'border': '1px solid #ddd'})
])

# ------------------------------------------------------------------------------
# 4. Page Rendering Functions
# ------------------------------------------------------------------------------
def render_landing_page():
    cards = []
    for t in TEMPLATE_GALLERY:
        card = html.Div([
            html.Div(t['icon'], style={'fontSize': '40px', 'marginBottom': '10px'}),
            html.H3(t['title'], style={'fontSize': '18px', 'marginBottom': '8px', 'color': '#333'}),
            html.P(t['desc'], style={'fontSize': '14px', 'color': '#666', 'lineHeight': '1.4'}),
            html.Button("Select", id={'type': 'tmpl-btn', 'index': t['id']}, 
                        style={'marginTop': '15px', 'padding': '8px 16px', 'backgroundColor': '#4a4e69', 'color': 'white', 'border': 'none', 'borderRadius': '6px', 'cursor': 'pointer'})
        ], style=card_style)
        cards.append(card)
    
    return html.Div([
        html.H1("Which optimization problem do you want to solve?", style={'textAlign': 'center', 'marginBottom': '40px', 'color': '#222'}),
        html.Div(cards, style={
            'display': 'grid', 
            'gridTemplateColumns': 'repeat(auto-fit, minmax(280px, 1fr))', 
            'gap': '20px'
        })
    ])

def render_workspace(mode):
    mode_info = next((item for item in TEMPLATE_GALLERY if item["id"] == mode), None)
    title = mode_info['title'] if mode_info else "Custom Mode"
    
    return html.Div([
        html.Div([
            html.Span(f"Selected Mode: {title}", style={'backgroundColor': '#e2e6ea', 'padding': '5px 10px', 'borderRadius': '15px', 'fontSize': '14px', 'fontWeight': '600'})
        ], style={'marginBottom': '20px'}),

        dcc.Tabs([
            dcc.Tab(label='STEP 1: Data Definition', children=[
                html.Div([
                    wizard_input_section,  
                    html.Div(id='add-msg', style={'marginBottom': '10px'}),
                    html.Button('Add to Table', id='add-btn', n_clicks=0, style={'width': '100%', 'padding': '12px', 'backgroundColor': '#4a4e69', 'color': 'white', 'border': 'none', 'borderRadius': '8px', 'cursor': 'pointer', 'fontSize': '16px'}),
                    
                    html.H4("📊 Defined Data List", style={'marginTop': '30px'}),
                    
                    # Variables Table
                    html.H5("Decision Variables", style={'color': '#007bff'}),
                    dash_table.DataTable(
                        id='var-table', 
                        columns=[{'name': i, 'id': i} for i in ['var_name', 'var_type', 'unit_num', 'index_range']], 
                        data=[], 
                        style_header=table_header_style, 
                        style_cell=table_cell_style
                    ),
                    
                    # Parameters Table
                    html.H5("Parameters", style={'color': '#28a745', 'marginTop': '20px'}),
                    dash_table.DataTable(
                        id='param-table', 
                        columns=[{'name': i, 'id': i} for i in ['var_name', 'value', 'unit_num', 'index_range']], 
                        data=[], 
                        style_header=table_header_style, 
                        style_cell=table_cell_style
                    ),
                ], style={'padding': '20px'})
            ]),
            dcc.Tab(label='STEP 2: Modeling & Solver', children=[
                modeling_section 
            ])
        ])
    ])

# ------------------------------------------------------------------------------
# 5. Main Layout
# ------------------------------------------------------------------------------
app.layout = html.Div([
    dcc.Store(id='current-mode', data='home'),  
    html.Div([
        html.H2("🧙‍♂️ OptiMystic Solver", style={'margin': 0, 'color': '#4a4e69'}),
        html.Button("🏠 Home", id='btn-home', style={'padding': '5px 10px', 'cursor': 'pointer', 'border': 'none', 'background': 'transparent'})
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '30px', 'borderBottom': '1px solid #eee', 'paddingBottom': '15px'}),

    html.Div(id='page-content')

], style=app_style)

# ------------------------------------------------------------------------------
# 6. Callbacks
# ------------------------------------------------------------------------------

# [Router] Navigation between Landing Page and Workspace
@app.callback(
    [Output('current-mode', 'data'),
     Output('page-content', 'children')],
    [Input({'type': 'tmpl-btn', 'index': ALL}, 'n_clicks'),
     Input('btn-home', 'n_clicks')],
    [State('current-mode', 'data')]
)
def navigate(tmpl_clicks, home_click, current_mode):
    ctx = callback_context
    if not ctx.triggered:
        return 'home', render_landing_page()

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'btn-home':
        return 'home', render_landing_page()
    
    if 'tmpl-btn' in button_id:
        import json
        try:
            clicked_id_dict = json.loads(button_id)
            selected_mode = clicked_id_dict['index']
            return selected_mode, render_workspace(selected_mode)
        except:
            return 'home', render_landing_page()

    return 'home', render_landing_page()

# [Wizard] Toggle Input Visibility based on User Selection
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

# [Wizard] Render Dynamic Index Inputs
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

# [Wizard] Add Data to Tables
@app.callback(
    [Output('var-table', 'data'),
     Output('param-table', 'data'),
     Output('add-msg', 'children'),
     Output('input-name', 'value')],
    Input('add-btn', 'n_clicks'),
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
    if n_clicks == 0: return dash.no_update, dash.no_update, "", ""
    if not name: return dash.no_update, dash.no_update, html.Span("❌ Please enter a name!", style={'color': '#dc3545', 'fontWeight': 'bold'}), dash.no_update

    # Initialize lists if they are None
    if var_rows is None: var_rows = []
    if param_rows is None: param_rows = []

    final_u_num = u_num if u_num else "-"
    final_u_denom = u_denom if u_denom else "1"

    if is_indexed == 'yes':
        final_num_indices = num_indices
        valid_ranges = [r for r in idx_ranges_list if r]
        final_range_str = ", ".join(valid_ranges)
    else:
        final_num_indices = 0
        final_range_str = "-"
        
    new_row = {
        'var_name': name, 
        'unit_num': final_u_num, 
        'unit_denom': final_u_denom,
        'num_indices': final_num_indices, 
        'index_range': final_range_str
    }

    if category == 'param':
        new_row['value'] = val if is_indexed == 'no' else "Matrix(TBD)"
        param_rows.append(new_row)
        return var_rows, param_rows, html.Span(f"✅ Added Parameter '{name}'", style={'color': '#28a745', 'fontWeight': 'bold'}), ""
    else:
        new_row['var_type'] = var_type
        var_rows.append(new_row)
        return var_rows, param_rows, html.Span(f"✅ Added Variable '{name}'", style={'color': '#007bff', 'fontWeight': 'bold'}), ""

# [Solver] Dummy Logic for Phase 2
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
    app.run_server(debug=True)
