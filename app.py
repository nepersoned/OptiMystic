import dash
from dash import html, dash_table, dcc, Input, Output, State, ALL, callback_context
import json
import solver_engine
import bridge_logic

# --- Server Start Notification ---
print("\n" + "="*50)
print("🏗️ UI PERFECTED: SCROLLBAR STABILIZED")
print("   - Scrollbar: ALWAYS VISIBLE (Prevents layout jumping)")
print("   - Tables: FIXED WIDTH & LEFT ALIGN (Iron Layout)")
print("   - Style: Modern Blue & Clean")
print("="*50 + "\n")

external_stylesheets = ['https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, title='OptiMystic Solver', suppress_callback_exceptions=True)
server = app.server

# --- Styles ---
app_wrapper_style = {
    'position': 'fixed', 'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
    'backgroundColor': '#eaeff2',
    'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center',
    'fontFamily': 'Inter, sans-serif'
}

main_box_style = {
    'width': '1200px', 'maxWidth': '95%', 'height': '90vh',
    'backgroundColor': 'white', 'borderRadius': '12px',
    'boxShadow': '0 10px 40px rgba(0,0,0,0.1)',
    'display': 'flex', 'flexDirection': 'column', 'overflow': 'hidden'
}

header_style = {
    'backgroundColor': '#4a4e69', 'padding': '0 25px', 'height': '55px',
    'flexShrink': 0, 'display': 'flex', 'justifyContent': 'space-between',
    'alignItems': 'center', 'color': 'white'
}

# [KEY FIX] Force Scrollbar Track ('scroll' instead of 'auto')
# This ensures the layout never jumps when switching tabs
content_area_style = {
    'flex': 1, 
    'overflowY': 'scroll',      # Always show scrollbar track
    'padding': '30px', 
    'backgroundColor': '#ffffff'
}

add_btn_style = {
    'width': '100%', 'padding': '10px', 'border': '2px dashed #dee2e6', 'borderRadius': '8px',
    'backgroundColor': 'transparent', 'color': '#007bff', 'fontWeight': '600', 'fontSize': '14px',
    'cursor': 'pointer', 'marginTop': '10px', 'transition': 'all 0.2s',
    'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center'
}

card_style = {
    'border': '1px solid #eee', 'borderRadius': '10px', 'padding': '20px',
    'textAlign': 'center', 'cursor': 'pointer', 'backgroundColor': 'white', 
    'boxShadow': '0 2px 8px rgba(0,0,0,0.03)', 'transition': 'transform 0.1s',
    'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'space-between', 'height': '200px'
}

tab_selected_style = {'borderTop': '3px solid #4a4e69', 'color': '#4a4e69', 'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'padding': '12px'}
tab_style = {'padding': '12px', 'color': '#888', 'backgroundColor': 'white', 'borderBottom': '1px solid #dee2e6'}
input_style = {'width': '100%', 'padding': '8px', 'borderRadius': '4px', 'border': '1px solid #ccc', 'marginBottom': '8px', 'boxSizing': 'border-box'}

# --- Table Styles (Iron Layout) ---
table_container_style = {'borderRadius': '8px', 'overflow': 'hidden', 'border': '1px solid #e9ecef', 'marginBottom': '10px'}

table_cell_style = {
    'padding': '12px 15px', 'border': 'none', 'borderBottom': '1px solid #f1f3f5', 
    'fontSize': '14px', 'fontFamily': 'Inter, sans-serif', 
    'textAlign': 'left', # Force Left
    'color': '#333',
    'minWidth': '100px', 'width': '100px', 'maxWidth': '150px',
    'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'nowrap'
}

table_header_style = {
    'backgroundColor': '#f8f9fa', 'color': '#495057', 'fontWeight': '600', 
    'textAlign': 'left', 'padding': '12px 15px', 'borderBottom': '2px solid #dee2e6'
}

table_conditional_style = [
    {'if': {'row_index': 'odd'}, 'backgroundColor': '#fcfcfc'},
    {'if': {'state': 'active'}, 'backgroundColor': '#f1f8ff', 'border': '2px solid #007bff', 'color': '#007bff'},
    {'if': {'state': 'selected'}, 'backgroundColor': '#f1f8ff', 'border': '2px solid #007bff', 'color': '#007bff'},
]

fixed_css = [
    {'selector': '.dash-cell', 'rule': 'text-align: left !important;'},
    {'selector': '.dash-header', 'rule': 'text-align: left !important;'},
    {'selector': '.dash-cell-value', 'rule': 'text-align: left !important;'}
]

TEMPLATE_GALLERY = [
    {"id": "cutting", "icon": "✂️", "title": "Cutting Stock", "desc": "Minimize waste (1D packing)."},
    {"id": "packing", "icon": "📦", "title": "Bin Packing", "desc": "Load trucks efficiently."},
    {"id": "blending", "icon": "🧪", "title": "Blending", "desc": "Optimize mixture recipes."},
    {"id": "prod_mix", "icon": "🏭", "title": "Production Mix", "desc": "Maximize profit."},
    {"id": "schedule", "icon": "📅", "title": "Scheduling", "desc": "Workforce rostering."},
    {"id": "transport", "icon": "🚚", "title": "Transportation", "desc": "Logistics cost min."},
    {"id": "custom", "icon": "🔮", "title": "Custom Mode", "desc": "Build from scratch."}
]

# ==========================================
# [SECTION 1] TEMPLATE UIs
# ==========================================
ui_cutting = html.Div([
    html.H4("✂️ Cutting Stock", style={'color': '#4a4e69', 'marginBottom': '5px'}),
    html.P("Minimize material waste.", style={'color': '#888', 'fontSize': '13px', 'marginBottom': '25px'}),
    html.Div([html.Label("Stock Length:", style={'fontWeight': 'bold'}), dcc.Input(id='cut-stock-len', type='number', value=1000, style=input_style)], style={'marginBottom': '15px'}),
    dash_table.DataTable(id='cut-table', columns=[{'name': 'Item Name', 'id': 'Item', 'editable': True}, {'name': 'Length', 'id': 'Length', 'type': 'numeric', 'editable': True}, {'name': 'Demand', 'id': 'Demand', 'type': 'numeric', 'editable': True}], data=[{'Item': 'Pipe_A', 'Length': 250, 'Demand': 50}, {'Item': 'Pipe_B', 'Length': 300, 'Demand': 30}], row_deletable=True, editable=True, 
                         style_table=table_container_style, style_header=table_header_style, style_cell=table_cell_style, style_data_conditional=table_conditional_style, css=fixed_css),
    html.Button("＋ Add Item", id='btn-add-cut', n_clicks=0, style=add_btn_style)
])

ui_packing = html.Div([
    html.H4("📦 Bin Packing", style={'color': '#4a4e69', 'marginBottom': '5px'}),
    html.P("Maximize loading efficiency.", style={'color': '#888', 'fontSize': '13px', 'marginBottom': '25px'}),
    html.Div([html.Label("Bin Capacity:", style={'fontWeight': 'bold'}), dcc.Input(id='pack-capacity', type='number', value=100, style=input_style)], style={'marginBottom': '15px'}),
    dash_table.DataTable(id='pack-table', columns=[{'name': 'Item ID', 'id': 'Item', 'editable': True}, {'name': 'Weight', 'id': 'Weight', 'type': 'numeric', 'editable': True}, {'name': 'Value', 'id': 'Value', 'type': 'numeric', 'editable': True}], data=[{'Item': 'Box_1', 'Weight': 20, 'Value': 50}, {'Item': 'Box_2', 'Weight': 30, 'Value': 60}], row_deletable=True, editable=True,
                         style_table=table_container_style, style_header=table_header_style, style_cell=table_cell_style, style_data_conditional=table_conditional_style, css=fixed_css),
    html.Button("＋ Add Item", id='btn-add-pack', n_clicks=0, style=add_btn_style)
])

ui_blending = html.Div([
    html.H4("🧪 Blending", style={'color': '#4a4e69', 'marginBottom': '5px'}),
    html.P("Optimize mixture recipes.", style={'color': '#888', 'fontSize': '13px', 'marginBottom': '25px'}),
    dash_table.DataTable(id='blend-table', columns=[{'name': 'Ingr', 'id': 'Ingr', 'editable': True}, {'name': 'Cost', 'id': 'Cost', 'type': 'numeric', 'editable': True}, {'name': 'NutA', 'id': 'NutA', 'type': 'numeric', 'editable': True}, {'name': 'NutB', 'id': 'NutB', 'type': 'numeric', 'editable': True}], data=[{'Ingr': 'Chicken', 'Cost': 5, 'NutA': 10, 'NutB': 2}, {'Ingr': 'Veggie', 'Cost': 2, 'NutA': 1, 'NutB': 10}], row_deletable=True, editable=True,
                         style_table=table_container_style, style_header=table_header_style, style_cell=table_cell_style, style_data_conditional=table_conditional_style, css=fixed_css),
    html.Button("＋ Add Ingredient", id='btn-add-blend', n_clicks=0, style=add_btn_style),
    html.Div([
        html.Label("Constraints (Min):", style={'fontWeight': 'bold', 'color': '#28a745', 'marginBottom': '10px', 'display': 'block'}),
        html.Div([
            html.Div([html.Label("Min NutA", style={'fontSize':'13px'}), dcc.Input(id='min-nuta', type='number', value=20, style=input_style)], style={'width': '48%'}),
            html.Div([html.Label("Min NutB", style={'fontSize':'13px'}), dcc.Input(id='min-nutb', type='number', value=30, style=input_style)], style={'width': '48%'})
        ], style={'display':'flex', 'gap':'4%'})
    ], style={'marginTop': '30px', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})
])

ui_prod_mix = html.Div([
    html.H4("🏭 Production Mix", style={'marginBottom': '5px', 'color': '#4a4e69'}),
    html.P("Maximize profit.", style={'color': '#888', 'fontSize': '13px', 'marginBottom': '25px'}),
    html.Label("1. Products & Profit", style={'fontWeight': 'bold', 'color': '#007bff', 'marginBottom': '10px', 'display': 'block'}),
    dash_table.DataTable(id='pm-products-table', columns=[{'name': 'Product Name', 'id': 'Product', 'editable': True}, {'name': 'Profit ($)', 'id': 'Profit', 'type': 'numeric', 'editable': True}], data=[{'Product': 'P1', 'Profit': 100}, {'Product': 'P2', 'Profit': 150}], row_deletable=True, editable=True,
                         style_table=table_container_style, style_header=table_header_style, style_cell=table_cell_style, style_data_conditional=table_conditional_style, css=fixed_css),
    html.Button("＋ Add Product", id='pm-add-prod-btn', n_clicks=0, style=add_btn_style),
    html.Div([
        html.Label("2. Resource Usage", style={'fontWeight': 'bold', 'color': '#28a745', 'marginBottom': '10px', 'display': 'block'}),
        html.Div(id='pm-resource-matrix-container', children="[Matrix Input - Wired in Phase 6-2]", style={'padding': '30px', 'backgroundColor': '#f9f9f9', 'border': '1px dashed #ccc', 'textAlign': 'center', 'borderRadius':'8px', 'color': '#999'})
    ], style={'marginTop': '30px'})
])

ui_schedule = html.Div([
    html.H4("📅 Scheduling", style={'color': '#4a4e69', 'marginBottom': '5px'}),
    html.P("Automate workforce rostering.", style={'color': '#888', 'fontSize': '13px', 'marginBottom': '25px'}),
    html.Div([html.Label("Shifts/Day:", style={'fontWeight': 'bold'}), dcc.Input(id='sched-shifts', type='number', value=3, style=input_style)], style={'marginBottom': '20px'}),
    html.Div(id='sched-matrix-container', children="[Matrix Input - Wired in Phase 6-2]", style={'padding': '30px', 'backgroundColor': '#f9f9f9', 'border': '1px dashed #ccc', 'textAlign': 'center', 'borderRadius':'8px'})
])

ui_transport = html.Div([
    html.H4("🚚 Transportation", style={'color': '#4a4e69', 'marginBottom': '5px'}),
    html.P("Logistics optimization.", style={'color': '#888', 'fontSize': '13px', 'marginBottom': '25px'}),
    html.Div([
        html.Div([
            html.Label("Supply", style={'fontWeight': 'bold', 'color': '#007bff', 'marginBottom': '10px', 'display': 'block'}),
            dash_table.DataTable(id='trans-supply', columns=[{'name':'Source','id':'Src'},{'name':'Cap','id':'Cap'}], data=[{'Src':'F1','Cap':100},{'Src':'F2','Cap':200}], editable=True, row_deletable=True,
                                 style_table=table_container_style, style_header=table_header_style, style_cell=table_cell_style, style_data_conditional=table_conditional_style, css=fixed_css),
            html.Button("＋ Add Source", id='btn-add-source', n_clicks=0, style=add_btn_style)
        ], style={'flex': 1, 'marginRight': '20px'}),
        html.Div([
            html.Label("Demand", style={'fontWeight': 'bold', 'color': '#d63384', 'marginBottom': '10px', 'display': 'block'}),
            dash_table.DataTable(id='trans-demand', columns=[{'name':'Dest','id':'Dst'},{'name':'Dem','id':'Dem'}], data=[{'Dst':'S1','Dem':150},{'Dst':'S2','Dem':150}], editable=True, row_deletable=True,
                                 style_table=table_container_style, style_header=table_header_style, style_cell=table_cell_style, style_data_conditional=table_conditional_style, css=fixed_css),
            html.Button("＋ Add Dest", id='btn-add-dest', n_clicks=0, style=add_btn_style)
        ], style={'flex': 1})
    ], style={'display': 'flex', 'marginBottom': '30px'}),
    html.Label("Cost Matrix", style={'fontWeight': 'bold', 'color': '#28a745'}),
    html.Div(id='trans-matrix-container', children="[Matrix Input - Wired in Phase 6-2]", style={'padding': '30px', 'backgroundColor': '#f9f9f9', 'border': '1px dashed #ccc', 'textAlign': 'center', 'borderRadius':'8px'})
])

# ==========================================
# [SECTION 2] CUSTOM WIZARD
# ==========================================
def render_custom_step1():
    return html.Div([
        html.H4("1. Data Wizard", style={'marginBottom': '5px', 'color': '#4a4e69'}),
        html.P("Define custom variables.", style={'color': '#888', 'fontSize': '13px', 'marginBottom': '20px'}),
        html.Div([
            html.Div([html.Label("Role", style={'fontWeight': 'bold', 'fontSize':'13px'}), dcc.RadioItems(id='input-role', options=[{'label': ' Var', 'value': 'var'}, {'label': ' Param', 'value': 'param'}], value='var', labelStyle={'display': 'inline-block', 'marginRight':'10px'})], style={'flex': 1}),
            html.Div([html.Label("Shape", style={'fontWeight': 'bold', 'fontSize':'13px'}), dcc.RadioItems(id='input-shape', options=[{'label': ' Scalar', 'value': 'scalar'}, {'label': ' Matrix', 'value': 'matrix'}, {'label': ' List', 'value': 'list'}], value='scalar', labelStyle={'display': 'inline-block', 'marginRight':'10px'})], style={'flex': 1}),
            html.Div([dcc.Input(id='input-name', type='text', placeholder="Name...", style=input_style)], style={'flex': 1}),
        ], style={'display': 'flex', 'gap': '15px', 'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '15px', 'alignItems':'center'}),

        html.Div(id='matrix-config-area', style={'display': 'none', 'padding': '10px', 'border': '1px dashed #ccc', 'marginBottom': '10px'}, children=[
            html.Div([dcc.Input(id='matrix-rows', placeholder="Rows", style={**input_style, 'width':'48%'}), dcc.Input(id='matrix-cols', placeholder="Cols", style={**input_style, 'width':'48%'})], style={'display':'flex', 'gap':'4%'}),
            html.Button("Gen Grid", id='btn-gen-matrix', n_clicks=0),
            html.Div(style={'marginTop': '10px'}, children=[dash_table.DataTable(id='matrix-data-table', columns=[{'name':'No Data','id':'dummy'}], data=[], editable=True, style_table=table_container_style, style_header=table_header_style, style_cell=table_cell_style, style_data_conditional=table_conditional_style, css=fixed_css)])
        ]),
        html.Div(id='list-config-area', style={'display': 'none', 'padding': '10px', 'border': '1px dashed #ccc', 'marginBottom': '10px'}, children=[
            dcc.Input(id='list-cols', placeholder="Cols (comma sep)", style=input_style),
            html.Button("Init List", id='btn-init-list', n_clicks=0),
            html.Div(id='list-input-container', style={'marginTop':'10px', 'display':'none'}, children=[dash_table.DataTable(id='list-data-table', columns=[{'name':'Col1','id':'col1'}], data=[], editable=True, row_deletable=True, style_table=table_container_style, style_header=table_header_style, style_cell=table_cell_style, style_data_conditional=table_conditional_style, css=fixed_css), html.Button("+ Row", id='btn-add-list-row', n_clicks=0)])
        ]),
        html.Div(id='val-input-box', style={'display':'none'}, children=[dcc.Input(id='input-value', type='number', placeholder="Value", style=input_style)]),
        html.Div(id='type-input-box', style={'display':'block', 'marginBottom':'10px'}, children=[dcc.Dropdown(id='input-var-type', options=['Continuous', 'Integer', 'Binary'], value='Continuous', clearable=False)]),

        html.Button('Add Data', id='add-btn', n_clicks=0, style={'width': '100%', 'padding': '10px', 'backgroundColor': '#4a4e69', 'color': 'white', 'border': 'none', 'borderRadius': '6px'}),
        html.Div(id='add-msg', style={'marginTop': '5px', 'fontSize':'13px', 'textAlign': 'center'}),
        
        html.H5("Defined Data", style={'color': '#4a4e69', 'marginTop':'20px', 'fontSize':'16px'}),
        html.Div([
            html.Div([html.Label("Variables", style={'fontSize':'13px'}), dash_table.DataTable(id='var-table', columns=[{'name':i,'id':i} for i in ['Name','Shape','Type']], data=[], style_header=table_header_style, style_cell=table_cell_style, style_table=table_container_style, style_data_conditional=table_conditional_style, css=fixed_css)], style={'flex':1, 'marginRight':'10px'}),
            html.Div([html.Label("Parameters", style={'fontSize':'13px'}), dash_table.DataTable(id='param-table', columns=[{'name':i,'id':i} for i in ['Name','Shape','Val']], data=[], style_header=table_header_style, style_cell=table_cell_style, style_table=table_container_style, style_data_conditional=table_conditional_style, css=fixed_css)], style={'flex':1})
        ], style={'display':'flex'})
    ])

# --- 3. Modeling & Dashboard ---
modeling_section = html.Div([
    html.H4("⚙️ Solver Engine", style={'marginBottom': '5px', 'color': '#4a4e69'}),
    html.P("Define objective and constraints.", style={'color': '#888', 'fontSize': '13px', 'marginBottom': '20px'}),

    html.Div([
        dcc.RadioItems(id='solver-sense', options=[{'label': ' Minimize', 'value': 'minimize'}, {'label': ' Maximize', 'value': 'maximize'}], value='minimize', labelStyle={'display': 'inline-block', 'marginRight': '20px'}),
        dcc.Textarea(id='solver-objective', placeholder="Objective...", style={'width': '100%', 'height': '60px', 'marginTop': '10px', 'border': '1px solid #ccc', 'padding': '10px', 'borderRadius': '4px'}),
        html.Label("Constraints:", style={'fontWeight': 'bold', 'marginTop': '15px', 'display': 'block'}),
        dcc.Textarea(id='solver-constraints', placeholder="Constraints...", style={'width': '100%', 'height': '150px', 'marginTop': '5px', 'border': '1px solid #ccc', 'padding': '10px', 'borderRadius': '4px'}),
        html.Button("🚀 Run Optimization", id='btn-solve', n_clicks=0, style={'width': '100%', 'marginTop':'20px', 'padding': '12px', 'backgroundColor': '#28a745', 'color': 'white', 'border': 'none', 'borderRadius': '6px', 'fontSize': '16px', 'fontWeight': 'bold'})
    ])
])

dashboard_section = html.Div([
    html.H4("📊 Result Dashboard", style={'marginBottom': '5px', 'color': '#4a4e69'}),
    html.P("Optimization results.", style={'color': '#888', 'fontSize': '13px', 'marginBottom': '20px'}),

    html.Div([
        html.Div([html.H6("Status", style={'margin':0, 'color':'#666'}), html.H3(id='res-status', children="-", style={'margin':'5px 0'})], style={**card_style, 'height': '100px', 'minHeight': 'unset', 'justifyContent': 'center'}), 
        html.Div([html.H6("Objective", style={'margin':0, 'color':'#666'}), html.H3(id='res-objective', children="-", style={'margin':'5px 0', 'color':'#007bff'})], style={**card_style, 'height': '100px', 'minHeight': 'unset', 'justifyContent': 'center'}),
    ], style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '15px', 'marginBottom': '20px'}),
    
    html.Div(id='result-dashboard', style={'display': 'none'}, children=[
        html.H6("Variables", style={'marginTop': '10px'}),
        dash_table.DataTable(id='res-table', columns=[{'name': 'Var', 'id': 'Variable'}, {'name': 'Val', 'id': 'Value'}], data=[], page_size=5, style_table=table_container_style, css=fixed_css, style_header=table_header_style, style_cell=table_cell_style, style_data_conditional=table_conditional_style),
        html.H6("Constraints", style={'marginTop': '20px'}),
        dash_table.DataTable(id='res-constraints-table', columns=[{'name': 'ID', 'id': 'Constraint'}, {'name': 'Shadow Price', 'id': 'Shadow Price'}, {'name': 'Slack', 'id': 'Slack'}], data=[], page_size=5, style_table=table_container_style, css=fixed_css, style_header=table_header_style, style_cell=table_cell_style, style_data_conditional=table_conditional_style)
    ]),
    html.Div(id='solver-error-msg', style={'color': '#dc3545', 'marginTop': '15px', 'whiteSpace': 'pre-wrap', 'fontWeight': 'bold'})
])

# --- Helper Functions ---
def render_landing_page():
    return html.Div([
        html.H1("OptiMystic Solver", style={'textAlign': 'center', 'marginBottom': '5px', 'color': '#4a4e69'}),
        html.P("Select a template:", style={'textAlign': 'center', 'marginBottom': '30px', 'color': '#888'}),
        html.Div([
            html.Div([
                html.Div(t['icon'], style={'fontSize': '32px', 'marginBottom': '10px'}), 
                html.H4(t['title'], style={'margin': '0 0 5px 0', 'fontSize': '16px'}),
                html.P(t['desc'], style={'fontSize': '12px', 'color': '#999', 'margin': '0 0 10px 0', 'lineHeight': '1.3'}),
                html.Button("Select", id={'type': 'tmpl-btn', 'index': t['id']}, style={'marginTop': 'auto', 'padding':'6px 20px', 'backgroundColor':'#4a4e69', 'color':'white', 'border':'none', 'borderRadius':'20px', 'cursor': 'pointer'})
            ], style=card_style) for t in TEMPLATE_GALLERY
        ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(220px, 1fr))', 'gap': '20px'})
    ], style={'maxWidth': '1000px', 'margin': '0 auto', 'width': '100%'})

def render_workspace(mode):
    mode_info = next((item for item in TEMPLATE_GALLERY if item["id"] == mode), None)
    title = mode_info['title'] if mode_info else "Custom Mode"
    if mode == 'cutting': content = ui_cutting
    elif mode == 'packing': content = ui_packing
    elif mode == 'blending': content = ui_blending
    elif mode == 'prod_mix': content = ui_prod_mix
    elif mode == 'schedule': content = ui_schedule
    elif mode == 'transport': content = ui_transport
    else: content = render_custom_step1()

    return html.Div([
        dcc.Store(id='all-data-store', data={'variables': [], 'parameters': []}),
        html.Div([
            dcc.Link("← Back", href='/home', style={'textDecoration': 'none', 'color': '#4a4e69', 'fontWeight': 'bold', 'marginRight': '15px'}),
            html.Span(f"{title}", style={'backgroundColor': '#e2e6ea', 'padding': '5px 15px', 'borderRadius': '20px', 'fontSize': '14px', 'fontWeight': 'bold'})
        ], style={'marginBottom': '15px', 'display': 'flex', 'alignItems': 'center'}),
        
        dcc.Tabs([
            dcc.Tab(label='1. Input', children=[html.Div(content, style={'padding': '20px'})], selected_style=tab_selected_style, style=tab_style),
            dcc.Tab(label='2. Solver', children=[html.Div(modeling_section, style={'padding': '20px'})], selected_style=tab_selected_style, style=tab_style),
            dcc.Tab(label='3. Result', children=[html.Div(dashboard_section, style={'padding': '20px'})], selected_style=tab_selected_style, style=tab_style)
        ])
    ])

# --- Main Layout ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div([
        html.Div([html.H3("🧙‍♂️ OptiMystic", style={'margin': 0, 'fontWeight': 'bold'}), dcc.Link("Home", href='/home', style={'color': 'white', 'textDecoration': 'none', 'fontWeight': 'bold'})], style=header_style),
        html.Div(id='page-content', style=content_area_style)
    ], style=main_box_style)
], style=app_wrapper_style)

# --- Router ---
@app.callback([Output('page-content', 'children'), Output('url', 'pathname')], [Input('url', 'pathname'), Input({'type': 'tmpl-btn', 'index': ALL}, 'n_clicks')], [State('url', 'pathname')])
def router(pathname, tmpl_clicks, current_path):
    ctx = callback_context
    if 'tmpl-btn' in (ctx.triggered[0]['prop_id'] if ctx.triggered else ''):
        mode = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])['index']
        return render_workspace(mode), f"/{mode}"
    mode = pathname.strip('/') if pathname else ''
    valid_ids = [t['id'] for t in TEMPLATE_GALLERY]
    if mode in valid_ids: return render_workspace(mode), pathname
    return render_landing_page(), "/home"

@app.callback(Output('cut-table', 'data'), Input('btn-add-cut', 'n_clicks'), State('cut-table', 'data'), prevent_initial_call=True)
def add_cut_row(n, data): return (data or []) + [{'Item': f'Item_{len(data or [])+1}', 'Length': 100, 'Demand': 10}]

@app.callback(Output('pack-table', 'data'), Input('btn-add-pack', 'n_clicks'), State('pack-table', 'data'), prevent_initial_call=True)
def add_pack_row(n, data): return (data or []) + [{'Item': f'Box_{len(data or [])+1}', 'Weight': 10, 'Value': 100}]

@app.callback(Output('blend-table', 'data'), Input('btn-add-blend', 'n_clicks'), State('blend-table', 'data'), prevent_initial_call=True)
def add_blend_row(n, data): return (data or []) + [{'Ingr': f'Ingr_{len(data or [])+1}', 'Cost': 1, 'NutA': 0, 'NutB': 0}]

@app.callback(Output('pm-products-table', 'data'), Input('pm-add-prod-btn', 'n_clicks'), State('pm-products-table', 'data'), prevent_initial_call=True)
def add_prod_row(n, data): return (data or []) + [{'Product': f'Prod_{len(data or [])+1}', 'Profit': 100}]

@app.callback(Output('trans-supply', 'data'), Input('btn-add-source', 'n_clicks'), State('trans-supply', 'data'), prevent_initial_call=True)
def add_source_row(n, data): return (data or []) + [{'Src': f'F{len(data or [])+1}', 'Cap': 100}]

@app.callback(Output('trans-demand', 'data'), Input('btn-add-dest', 'n_clicks'), State('trans-demand', 'data'), prevent_initial_call=True)
def add_dest_row(n, data): return (data or []) + [{'Dst': f'S{len(data or [])+1}', 'Dem': 100}]

@app.callback([Output('matrix-config-area', 'style'), Output('list-config-area', 'style'), Output('val-input-box', 'style'), Output('type-input-box', 'style')], [Input('input-role', 'value'), Input('input-shape', 'value')])
def toggle_inputs(role, shape):
    return ({'display':'block','padding':'10px','border':'1px dashed #ccc','marginBottom':'10px'} if shape=='matrix' else {'display':'none'}), \
           ({'display':'block','padding':'10px','border':'1px dashed #ccc','marginBottom':'10px'} if shape=='list' else {'display':'none'}), \
           ({'display':'block','marginBottom':'15px'} if role=='param' and shape=='scalar' else {'display':'none'}), \
           ({'display':'block','marginBottom':'15px'} if role=='var' else {'display':'none'})

@app.callback([Output('matrix-data-table', 'data'), Output('matrix-data-table', 'columns'), Output('matrix-data-table', 'style_table')], Input('btn-gen-matrix', 'n_clicks'), [State('matrix-rows', 'value'), State('matrix-cols', 'value')])
def generate_matrix(n, r_str, c_str):
    if n==0: return [], [{'name':'No Data','id':'dummy'}], {'display':'none'}
    rows = [r.strip() for r in r_str.split(',')] if r_str else ['R1']
    cols = [c.strip() for c in c_str.split(',')] if c_str else ['C1']
    return [{'row_label': r, **{c: 0 for c in cols}} for r in rows], [{'name':'Label','id':'row_label','editable':False}]+[{'name':c,'id':c,'type':'numeric'} for c in cols], {'overflowX':'auto','display':'block'}

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
    if role == 'var':
        v_rows.append({'Name': name, 'Shape': shape, 'Type': vtype, 'Preview': '-'})
        store['variables'].append({'name': name, 'shape': shape, 'type': vtype, 'data': r_data})
        msg = html.Span(f"✅ Added Var: {name}", style={'color':'blue'})
    else:
        p_rows.append({'Name': name, 'Shape': shape, 'Value/Preview': prev})
        store['parameters'].append({'name': name, 'shape': shape, 'data': r_data})
        msg = html.Span(f"✅ Added Param: {name}", style={'color':'green'})
    return v_rows, p_rows, store, msg, ""

@app.callback([Output('result-dashboard', 'style'), Output('res-status', 'children'), Output('res-status', 'style'), Output('res-objective', 'children'), Output('res-table', 'data'), Output('res-constraints-table', 'data'), Output('solver-error-msg', 'children')], Input('btn-solve', 'n_clicks'), [State('solver-sense', 'value'), State('solver-objective', 'value'), State('solver-constraints', 'value'), State('all-data-store', 'data')])
def run_solver(n, sense, obj, const, store):
    if n==0 or not obj: return {'display':'none'}, "-", {}, "-", [], [], ""
    res = solver_engine.solve_model(store, sense, obj, const)
    if res.get('status') == 'Error': return {'display':'none'}, "Error", {'color':'#dc3545'}, "-", [], [], f"System Error:\n{res.get('error_msg')}"
    return {'display':'block'}, res['status'], ({'color':'#28a745'} if res['status']=='Optimal' else {'color':'#ffc107'}), f"{res['objective']:,.2f}", res['variables'], res['constraints'], ""

@app.callback(
    [Output('solver-objective', 'value'),
     Output('solver-constraints', 'value'),
     Output('all-data-store', 'data', allow_duplicate=True)],
    [Input('btn-solve', 'n_clicks')],
    [State('url', 'pathname'),
     State('trans-supply', 'data'),
     State('trans-demand', 'data'),
     State('blend-table', 'data'),
     State('min-nuta', 'value'),
     State('min-nutb', 'value')],
    prevent_initial_call=True
)
def sync_bridge_to_ui(n, pathname, trans_supply, trans_demand, blend_data, min_a, min_b):
    mode = pathname.strip('/')
    
    # Prepare Parameters for the Bridge
    if mode == 'transportation':
        params = {
            'Plants': [r['Src'] for r in trans_supply],
            'Regions': [r['Dst'] for r in trans_demand],
            'Supply': {r['Src']: r['Cap'] for r in trans_supply},
            'Demand': {r['Dst']: r['Dem'] for r in trans_demand}
            # Note: Cost matrix logic will be linked here in Phase 6-2 finish
        }
    elif mode == 'blending':
        params = {
            'Ingredients': [r['Ingr'] for r in blend_data],
            'Cost': {r['Ingr']: r['Cost'] for r in blend_data},
            'NutA': {r['Ingr']: r['NutA'] for r in blend_data},
            'NutB': {r['Ingr']: r['NutB'] for r in blend_data},
            'min_a': min_a,
            'min_b': min_b
        }
    else:
        return dash.no_update, dash.no_update, dash.no_update

    # Call the Bridge
    obj, const, vars_config = bridge_logic.generate_logic(mode, params)
    
    # Build Store (Variables + Parameters)
    # The parameters also need to be sent to symbol_table for 'eval' to work
    store_data = {
        'variables': vars_config,
        'parameters': [{'name': k, 'shape': 'list' if isinstance(v, list) else 'scalar', 'data': v} for k, v in params.items()]
    }
    
    return obj, const, store_data

if __name__ == '__main__':
    app.run_server(debug=True)	
