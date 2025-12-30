import dash
from dash import html, dash_table, dcc, Input, Output, State, ALL, callback_context, no_update
import json
import pandas as pd
import plotly.express as px
import solver_engine
import bridge_logic

# [CHANGED] Import 'analytics' instead of 'view'
import modules.cutting.analytics as cut_analytics
from common.styles import *

# --- Server Start ---
print("\n" + "="*50)
print("🚀 OPTIMYSTIC: MODULAR ARCHITECTURE V2")
print("   - Module: 'modules.cutting.analytics' integrated")
print("   - Styles: 'common.styles' integrated")
print("="*50 + "\n")

external_stylesheets = ['https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, title='OptiMystic Solver', suppress_callback_exceptions=True)
server = app.server

# --- Global Layout Styles ---
app_wrapper_style = {'position': 'fixed', 'top': 0, 'left': 0, 'right': 0, 'bottom': 0, 'backgroundColor': '#eaeff2', 'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'fontFamily': 'Inter, sans-serif'}
main_box_style = {'width': '1280px', 'maxWidth': '96%', 'height': '92vh', 'backgroundColor': 'white', 'borderRadius': '16px', 'boxShadow': '0 20px 60px rgba(0,0,0,0.08)', 'display': 'flex', 'flexDirection': 'column', 'overflow': 'hidden'}
header_style = {'backgroundColor': '#4a4e69', 'padding': '0 30px', 'height': '65px', 'flexShrink': 0, 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'color': 'white'}
content_area_style = {'flex': 1, 'overflowY': 'auto', 'padding': '40px', 'backgroundColor': '#ffffff'}
card_style = {'backgroundColor': 'white', 'borderRadius': '12px', 'padding': '25px', 'border': '1px solid #f1f5f9', 'boxShadow': '0 4px 15px rgba(0, 0, 0, 0.03)', 'textAlign': 'center', 'height': 'auto', 'minHeight': '140px', 'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center', 'transition': 'transform 0.2s'}
tab_selected_style = {'borderTop': '3px solid #4a4e69', 'color': '#4a4e69', 'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'padding': '14px'}
tab_style = {'padding': '14px', 'color': '#888', 'backgroundColor': 'white', 'borderBottom': '1px solid #dee2e6'}

TEMPLATE_GALLERY = [{"id": "cutting", "icon": "✂️", "title": "Cutting Stock", "desc": "Minimize cost or maximize profit."}, {"id": "packing", "icon": "📦", "title": "Bin Packing", "desc": "Load trucks efficiently."}, {"id": "blending", "icon": "🧪", "title": "Blending", "desc": "Optimize mixture recipes."}, {"id": "prod_mix", "icon": "🏭", "title": "Production Mix", "desc": "Maximize profit."}, {"id": "schedule", "icon": "📅", "title": "Scheduling", "desc": "Workforce rostering."}, {"id": "transport", "icon": "🚚", "title": "Transportation", "desc": "Logistics cost min."}, {"id": "inventory", "icon": "📦", "title": "Inventory Opt", "desc": "Prevent stockouts & Reduce costs."}, {"id": "investment", "icon": "💰", "title": "Investment", "desc": "Maximize ROI within budget."}]

# --- Simple Templates (Legacy) ---
ui_packing = html.Div([html.H4("📦 Bin Packing"), dash_table.DataTable(id='pack-table', columns=[{'name':'Item','id':'Item'},{'name':'Weight','id':'Weight'},{'name':'Value','id':'Value'}], data=[{'Item': 'Box1', 'Weight': 30, 'Value': 50}], editable=True, row_deletable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add", id='btn-add-pack', style=ADD_BTN_STYLE)])
ui_blending = html.Div([html.H4("🧪 Blending"), dash_table.DataTable(id='blend-table', columns=[{'name':'Ingr','id':'Ingr'},{'name':'Cost','id':'Cost'},{'name':'NutA','id':'NutA'},{'name':'NutB','id':'NutB'}], data=[{'Ingr': 'A', 'Cost': 10, 'NutA': 1, 'NutB': 2}], editable=True, row_deletable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add", id='btn-add-blend', style=ADD_BTN_STYLE)])
ui_prod_mix = html.Div([html.H4("🏭 Production Mix"), dash_table.DataTable(id='pm-products-table', columns=[{'name':'Product','id':'Product'},{'name':'Profit','id':'Profit'}], data=[{'Product': 'P1', 'Profit': 100}], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), dash_table.DataTable(id='pm-resource-matrix', columns=[{'name':'Resource','id':'resource'}, {'name': 'Availability', 'id': 'avail'}], data=[{'resource': 'Labor', 'avail': 100}], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add Prod", id='pm-add-prod-btn', style=ADD_BTN_STYLE), html.Button("Add Res", id='pm-add-res-btn', style=ADD_BTN_STYLE)])
ui_schedule = html.Div([html.H4("📅 Scheduling"), dash_table.DataTable(id='sched-matrix', columns=[{'name':'Staff','id':'staff'}], data=[{'staff': 'Staff1'}], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add", id='btn-add-staff', style=ADD_BTN_STYLE)])
ui_transport = html.Div([html.H4("🚚 Transportation"), dash_table.DataTable(id='trans-supply', columns=[{'name':'Src','id':'Src'}, {'name': 'Cap', 'id': 'Cap'}], data=[{'Src': 'F1', 'Cap': 100}], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), dash_table.DataTable(id='trans-demand', columns=[{'name':'Dst','id':'Dst'}, {'name': 'Dem', 'id': 'Dem'}], data=[{'Dst': 'S1', 'Dem': 50}], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), dash_table.DataTable(id='trans-cost-matrix', columns=[{'name':'Label','id':'label'}], data=[], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add Src", id='btn-add-source', style=ADD_BTN_STYLE), html.Button("Add Dst", id='btn-add-dest', style=ADD_BTN_STYLE)])
ui_inventory = html.Div([html.H4("📦 Inventory"), dash_table.DataTable(id='inv-table', columns=[{'name':'Item','id':'Item'}, {'name': 'Demand', 'id': 'Demand'}, {'name': 'Cost', 'id': 'Cost'}], data=[], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add", id='btn-add-inv', style=ADD_BTN_STYLE)])
ui_investment = html.Div([html.H4("💰 Investment"), dash_table.DataTable(id='invest-table', columns=[{'name':'Project','id':'Project'}, {'name': 'Cost', 'id': 'Cost'}, {'name': 'Return', 'id': 'Return'}], data=[], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add", id='btn-add-invest', style=ADD_BTN_STYLE)])

# --- 3. Modeling & Dashboard ---
modeling_section = html.Div([
    html.Div([html.H4("⚙️ Solver Configuration", style={'color': '#4a4e69', 'fontWeight': '700', 'marginBottom': '8px'}), html.P("Configure how the AI solves your problem.", style={'color': '#888', 'fontSize': '13px'})], style={'marginBottom': '30px'}),
    html.Div([html.Label("Optimization Goal", style={'fontSize': '12px', 'fontWeight': '700', 'textTransform': 'uppercase', 'color': '#888', 'marginBottom': '10px', 'display': 'block', 'letterSpacing': '0.5px'}), dcc.RadioItems(id='solver-sense', options=[{'label': ' Minimize Cost', 'value': 'minimize'}, {'label': ' Maximize Profit', 'value': 'maximize'}], value='minimize', labelStyle={'display': 'block', 'marginBottom': '8px', 'fontWeight': '600', 'color': '#4a4e69', 'cursor': 'pointer'}, inputStyle={'marginRight': '10px'})], style={'backgroundColor': '#f8f9fa', 'padding': '25px', 'borderRadius': '12px', 'marginBottom': '25px', 'border': '1px solid #e9ecef'}),
    html.Details([html.Summary("🔧 Advanced: View/Edit Mathematical Model", style={'cursor': 'pointer', 'fontWeight': '600', 'color': '#007bff', 'fontSize': '14px'}), html.Div([html.Label("Objective Function:", style={'fontWeight': 'bold', 'marginTop': '15px', 'display': 'block', 'fontSize': '13px'}), dcc.Textarea(id='solver-objective', style={'width': '100%', 'height': '80px', 'border': '1px solid #ccc', 'padding': '12px', 'borderRadius': '8px', 'fontFamily': 'monospace', 'backgroundColor': '#fcfcfc', 'marginTop': '5px', 'fontSize': '12px'}), html.Label("Constraints:", style={'fontWeight': 'bold', 'marginTop': '15px', 'display': 'block', 'fontSize': '13px'}), dcc.Textarea(id='solver-constraints', style={'width': '100%', 'height': '150px', 'border': '1px solid #ccc', 'padding': '12px', 'borderRadius': '8px', 'fontFamily': 'monospace', 'backgroundColor': '#fcfcfc', 'marginTop': '5px', 'fontSize': '12px'})], style={'padding': '20px', 'border': '1px solid #eee', 'borderRadius': '12px', 'marginTop': '10px', 'backgroundColor': 'white'})], style={'marginBottom': '30px'}),
    html.Button("🚀 Run Optimization Engine", id='btn-solve', n_clicks=0, style=PRIMARY_BTN_STYLE)
])

dashboard_section = html.Div([
    html.H4("📊 Optimization Results", style={'color': '#4a4e69', 'fontWeight': '700', 'marginBottom': '25px'}),
    
    html.Div([
        html.Div([ # Cards
            html.Div([html.H6("Solver Status", style={'margin':0, 'color':'#888', 'fontWeight':'600', 'fontSize': '13px', 'textTransform': 'uppercase'}), html.H3(id='res-status', children="-", style={'margin':'10px 0', 'fontWeight':'800', 'fontSize': '28px', 'color': '#333'})], style=card_style), 
            html.Div([html.H6(id='res-obj-label', children="Total Cost", style={'margin':0, 'color':'#888', 'fontWeight':'600', 'fontSize': '13px', 'textTransform': 'uppercase'}), html.H3(id='res-objective', children="-", style={'margin':'10px 0', 'fontWeight':'800', 'color':'#007bff', 'fontSize': '28px'})], style=card_style),
        ], style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px'}),
        
        # Insight
        html.Div(id='res-insight-card', style={'backgroundColor': '#e3f2fd', 'padding': '25px', 'borderRadius': '12px', 'display': 'none'}, children=[html.H5("💡 Insight", style={'color': '#0d47a1', 'fontWeight': '700', 'marginTop': 0, 'marginBottom': '10px'}), dcc.Markdown(id='res-insight-text', style={'fontSize': '15px', 'lineHeight': '1.6', 'color': '#0d47a1', 'margin': 0})]),
        
        # Error
        html.Div(id='solver-error-msg', style={'display': 'none'}),
        
        html.Div(id='result-dashboard', style={'display': 'none'}, children=[
            html.Div([html.H5("✂️ Visual Cutting Plan", style={'color': '#4a4e69', 'fontWeight':'700', 'borderBottom': '1px solid #eee', 'paddingBottom': '15px', 'marginTop': 0}), dcc.Graph(id='res-chart', style={'height': '350px'})], style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '16px', 'border': '1px solid #f1f5f9', 'boxShadow': '0 4px 6px -1px rgba(0, 0, 0, 0.05)', 'marginBottom': '30px'}),
            html.Div([
                html.Div([html.H6("📋 Detailed Job Instructions", style={'fontWeight': '700', 'marginBottom': '15px', 'color': '#334155'}), dash_table.DataTable(id='res-table', columns=[{'name': 'Stock ID', 'id': 'Stock'}, {'name': 'Details', 'id': 'Plan'}, {'name': 'Usage/Value', 'id': 'Usage'}], data=[], page_size=10, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE)], style={'flex': 1}),
                html.Div(id='constraints-wrapper', children=[html.H6("🚧 Constraints & Bottlenecks", style={'fontWeight': '700', 'marginBottom': '15px', 'color': '#334155'}), dash_table.DataTable(id='res-constraints-table', columns=[{'name': 'Constraint', 'id': 'Constraint'}, {'name': 'Shadow Price', 'id': 'Shadow Price'}, {'name': 'Slack', 'id': 'Slack'}], data=[], page_size=10, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE)], style={'flex': 1})
            ], style={'display': 'flex', 'gap': '30px', 'flexWrap': 'wrap'})
        ])
    ], style={'display': 'flex', 'flexDirection': 'column', 'gap': '30px'})
])

def render_landing_page():
    return html.Div([
        html.H1("OptiMystic Solver", style={'textAlign': 'center', 'marginBottom': '10px', 'color': '#4a4e69', 'fontWeight': '800'}),
        html.P("Select a template to begin optimization:", style={'textAlign': 'center', 'marginBottom': '40px', 'color': '#888'}),
        html.Div([
            html.Div([
                html.Div(t['icon'], style={'fontSize': '40px', 'marginBottom': '15px'}),
                html.H4(t['title'], style={'margin': '0 0 5px 0', 'fontSize': '16px', 'fontWeight': 'bold'}),
                html.P(t['desc'], style={'fontSize': '13px', 'color': '#888', 'lineHeight': '1.5', 'marginBottom': '20px', 'flex': 1}),
                html.Button("Select", id={'type': 'tmpl-btn', 'index': t['id']}, style={'width': '100%', 'padding': '10px', 'borderRadius': '6px', 'border': 'none', 'backgroundColor': '#f1f3f5', 'color': '#4a4e69', 'fontWeight': '600', 'cursor': 'pointer', 'transition': '0.2s'})
            ], style=card_style) for t in TEMPLATE_GALLERY
        ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, 1fr)', 'gap': '25px', 'maxWidth': '1200px', 'margin': '0 auto'})
    ], style={'padding': '40px'})

def render_workspace(mode):
    mode_info = next((item for item in TEMPLATE_GALLERY if item["id"] == mode), None)
    title = mode_info['title'] if mode_info else "OptiMystic"
    
    # [CHANGED] Use 'analytics' module functions
    mapping = {
        'cutting': cut_analytics.render_input(), 
        'packing': ui_packing, 'blending': ui_blending, 'prod_mix': ui_prod_mix, 
        'schedule': ui_schedule, 'transport': ui_transport, 'inventory': ui_inventory, 'investment': ui_investment
    }
    
    ui_stack = []
    for m_key, component in mapping.items():
        style = {'display': 'block'} if m_key == mode else {'display': 'none'}
        ui_stack.append(html.Div(component, style=style))
    return html.Div([
        dcc.Store(id='all-data-store', data={'variables': [], 'parameters': []}),
        html.Div([dcc.Link("← Back", href='/home', style={'textDecoration':'none','color':'#4a4e69','fontWeight':'bold','marginRight':'15px'}), html.Span(f"{title}", style={'backgroundColor':'#e2e6ea','padding':'6px 18px','borderRadius':'30px','fontSize':'14px','fontWeight':'bold', 'color': '#4a4e69'})], style={'marginBottom':'20px','display':'flex','alignItems':'center'}),
        dcc.Tabs(id='main-tabs', value='tab-1', children=[
            dcc.Tab(label='1. Input', value='tab-1', children=[html.Div(ui_stack, style={'padding':'30px'})], selected_style=tab_selected_style, style=tab_style),
            dcc.Tab(label='2. Solver', value='tab-2', children=[html.Div(modeling_section, style={'padding':'30px'})], selected_style=tab_selected_style, style=tab_style),
            dcc.Tab(label='3. Result', value='tab-3', children=[html.Div(dashboard_section, style={'padding':'30px'})], selected_style=tab_selected_style, style=tab_style)
        ])
    ])

app.layout = html.Div([dcc.Location(id='url', refresh=False), html.Div([html.Div([html.H3("🧙‍♂️ OptiMystic", style={'margin':0,'fontWeight':'800', 'fontSize': '24px'}), dcc.Link("Home", href='/home', style={'color':'white','textDecoration':'none','fontWeight':'600', 'fontSize': '14px'})], style=header_style), html.Div(id='page-content', style=content_area_style)], style=main_box_style)], style=app_wrapper_style)

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

# --- Callbacks ---
@app.callback(Output('cut-stock-table', 'data'), Input('btn-add-stock', 'n_clicks'), State('cut-stock-table', 'data'), prevent_initial_call=True)
def add_stock_row(n, data): return (data or []) + [{'Name': f'Stock_{len(data or [])+1}', 'Length': 5000, 'Cost': 50, 'Limit': 100}]
@app.callback(Output('cut-table', 'data'), Input('btn-add-cut', 'n_clicks'), State('cut-table', 'data'), prevent_initial_call=True)
def add_cut_row(n, data): return (data or []) + [{'Item': f'Item_{len(data or [])+1}', 'Length': 100, 'Demand': 10, 'Price': 20}]
@app.callback(Output('pack-table', 'data'), Input('btn-add-pack', 'n_clicks'), State('pack-table', 'data'), prevent_initial_call=True)
def add_pack_row(n, data): return (data or []) + [{'Item': f'Item_{len(data or [])+1}', 'Weight': 10, 'Value': 100}]
@app.callback(Output('blend-table', 'data'), Input('btn-add-blend', 'n_clicks'), State('blend-table', 'data'), prevent_initial_call=True)
def add_blend_row(n, data): return (data or []) + [{'Ingr': f'Ingr_{len(data or [])+1}', 'Cost': 1, 'NutA': 0, 'NutB': 0}]
@app.callback(Output('pm-products-table', 'data'), Input('pm-add-prod-btn', 'n_clicks'), State('pm-products-table', 'data'), prevent_initial_call=True)
def add_prod_row(n, data): return (data or []) + [{'Product': f'Prod_{len(data or [])+1}', 'Profit': 100}]
@app.callback(Output('trans-supply', 'data'), Input('btn-add-source', 'n_clicks'), State('trans-supply', 'data'), prevent_initial_call=True)
def add_source_row(n, data): return (data or []) + [{'Src': f'F{len(data or [])+1}', 'Cap': 100}]
@app.callback(Output('trans-demand', 'data'), Input('btn-add-dest', 'n_clicks'), State('trans-demand', 'data'), prevent_initial_call=True)
def add_dest_row(n, data): return (data or []) + [{'Dst': f'S{len(data or [])+1}', 'Dem': 100}]
@app.callback(Output('inv-table', 'data'), Input('btn-add-inv', 'n_clicks'), State('inv-table', 'data'), prevent_initial_call=True)
def add_inv_row(n, data): return (data or []) + [{'Item': f'Item_{len(data or [])+1}', 'Demand': 100, 'Cost': 10}]
@app.callback(Output('invest-table', 'data'), Input('btn-add-invest', 'n_clicks'), State('invest-table', 'data'), prevent_initial_call=True)
def add_invest_row(n, data): return (data or []) + [{'Project': f'Proj_{len(data or [])+1}', 'Cost': 10000, 'Return': 15000}]
@app.callback(Output('pm-resource-matrix', 'data'), Input('pm-add-res-btn', 'n_clicks'), State('pm-resource-matrix', 'data'), State('pm-resource-matrix', 'columns'), prevent_initial_call=True)
def add_pm_res_row(n, data, cols): return (data or []) + [{c['id']: (f"Res_{len(data)+1}" if c['id'] == 'resource' else 0) for c in cols}]
@app.callback(Output('sched-matrix', 'data'), Input('btn-add-staff', 'n_clicks'), State('sched-matrix', 'data'), State('sched-matrix', 'columns'), prevent_initial_call=True)
def add_sched_staff_row(n, data, cols): return (data or []) + [{c['id']: (f"Staff_{len(data)+1}" if c['id'] == 'staff' else 0) for c in cols}]

@app.callback(
    [Output('solver-objective', 'value'), Output('solver-constraints', 'value'), Output('all-data-store', 'data')],
    [Input('cut-table', 'data'), Input('cut-stock-table', 'data'), 
     Input('pack-table', 'data'), Input('blend-table', 'data'), Input('pm-products-table', 'data'), Input('pm-resource-matrix', 'data'), Input('sched-matrix', 'data'), Input('trans-supply', 'data'), Input('trans-demand', 'data'), Input('trans-cost-matrix', 'data'), Input('inv-table', 'data'), Input('invest-table', 'data'),
     Input('solver-sense', 'value'), Input('url', 'pathname')]
)
def sync_bridge_data(cut_data, stock_data, pack_data, blend_data, pm_prod, pm_res, sched_data, trans_src, trans_dst, trans_cost, inv_data, invest_data, sense, pathname):
    mode = pathname.strip('/') if pathname else ''
    params = {}
    param_list = []
    
    # [CHANGED] Use 'analytics' module logic
    if mode == 'cutting':
        data_inputs = {'cut_table': cut_data, 'cut_stock_table': stock_data}
        params, param_list = cut_analytics.get_params(data_inputs, sense)
    
    # ... (Other templates) ...
    elif mode == 'packing':
        if not pack_data: pack_data = []
        items = [r['Item'] for r in pack_data if r.get('Item')]
        weights = {r['Item']: float(r['Weight']) for r in pack_data if r.get('Item')}
        values = {r['Item']: float(r['Value']) for r in pack_data if r.get('Item')}
        params = {'Items': items, 'Weights': weights, 'Values': values, 'Capacity': 100}
        param_list = [{'name':'Weights','shape':'dict','data':weights}, {'name':'Values','shape':'dict','data':values}]
    
    elif mode == 'blending':
        if not blend_data: blend_data = []
        ingr = [r['Ingr'] for r in blend_data if r.get('Ingr')]
        cost = {r['Ingr']: float(r['Cost']) for r in blend_data if r.get('Ingr')}
        nut_a = {r['Ingr']: float(r['NutA']) for r in blend_data if r.get('Ingr')}
        nut_b = {r['Ingr']: float(r['NutB']) for r in blend_data if r.get('Ingr')}
        params = {'Ingredients': ingr, 'Cost': cost, 'NutA': nut_a, 'NutB': nut_b, 'min_a': 20, 'min_b': 30}
        param_list = [{'name':'Cost','shape':'dict','data':cost}, {'name':'NutA','shape':'dict','data':nut_a}, {'name':'NutB','shape':'dict','data':nut_b}]

    elif mode == 'prod_mix':
        if not pm_prod: pm_prod = []
        products = [r['Product'] for r in pm_prod if r.get('Product')]
        profit = {r['Product']: float(r['Profit']) for r in pm_prod if r.get('Product')}
        params = {'Products': products, 'Profit': profit}
        param_list = [{'name':'Profit', 'shape':'dict', 'data':profit}]

    elif mode == 'transportation':
        if not trans_src: trans_src = []
        if not trans_dst: trans_dst = []
        plants = [r['Src'] for r in trans_src if r.get('Src')]
        regions = [r['Dst'] for r in trans_dst if r.get('Dst')]
        supply = {r['Src']: float(r['Cap']) for r in trans_src if r.get('Src')}
        demand = {r['Dst']: float(r['Dem']) for r in trans_dst if r.get('Dst')}
        params = {'Plants': plants, 'Regions': regions, 'Supply': supply, 'Demand': demand}
        param_list = [{'name':'Supply', 'shape':'dict', 'data':supply}, {'name':'Demand', 'shape':'dict', 'data':demand}]

    elif mode == 'schedule':
        if not sched_data: sched_data = []
        staff = [r['Staff'] for r in sched_data if r.get('Staff')]
        params = {'Staff': staff}
        param_list = []

    elif mode == 'inventory':
        if not inv_data: inv_data = []
        items = [r['Item'] for r in inv_data if r.get('Item')]
        demand = {r['Item']: float(r['Demand']) for r in inv_data if r.get('Item')}
        params = {'Items': items, 'Demand': demand}
        param_list = [{'name':'Demand', 'shape':'dict', 'data':demand}]

    elif mode == 'investment':
        if not invest_data: invest_data = []
        projects = [r['Project'] for r in invest_data if r.get('Project')]
        cost = {r['Project']: float(r['Cost']) for r in invest_data if r.get('Project')}
        ret = {r['Project']: float(r['Return']) for r in invest_data if r.get('Project')}
        params = {'Projects': projects, 'Cost': cost, 'Return': ret, 'Budget': 100000}
        param_list = [{'name':'Cost', 'shape':'dict', 'data':cost}, {'name':'Return', 'shape':'dict', 'data':ret}]

    obj, const, vars_config = bridge_logic.generate_logic(mode, params)
    return obj, const, {'variables': vars_config, 'parameters': param_list}

@app.callback(
    [Output('result-dashboard', 'style'), Output('res-status', 'children'), Output('res-status', 'style'), 
     Output('res-objective', 'children'), Output('res-obj-label', 'children'),
     Output('res-table', 'data'), Output('res-constraints-table', 'data'), Output('res-chart', 'figure'), Output('res-insight-card', 'style'), Output('res-insight-text', 'children'), Output('solver-error-msg', 'children'), Output('solver-error-msg', 'style'), Output('constraints-wrapper', 'style'), Output('main-tabs', 'value')],
    [Input('btn-solve', 'n_clicks')],
    [State('solver-sense', 'value'), State('solver-objective', 'value'), State('solver-constraints', 'value'), State('all-data-store', 'data'), State('main-tabs', 'value'), State('url', 'pathname')]
)
def run_solver(n, sense, obj, const, store, current_tab, pathname):
    if n == 0 or not obj: return {'display':'none'}, "-", {}, "-", "Total Objective", [], [], {}, {'display':'none'}, "", "", {'display':'none'}, {'display':'block'}, no_update
    
    mode = pathname.strip('/') if pathname else ''
    res = solver_engine.solve_model(store, sense, obj, const)
    
    if res.get('status') == 'Error':
        error_style = {'display':'block', 'color': '#c0392b', 'backgroundColor': '#fceae9', 'border': '1px solid #f5c6cb', 'borderRadius': '12px', 'padding': '25px', 'whiteSpace': 'pre-wrap', 'fontWeight': '500', 'marginBottom': '30px', 'marginTop': '30px'}
        friendly_error = html.Div([
            html.H5("🚨 Optimization Failed", style={'margin': '0 0 10px 0', 'fontWeight': 'bold', 'color': '#c0392b'}),
            html.P("The solver could not find a solution. Please check:", style={'marginBottom': '10px', 'color': '#333'}),
            html.Ul([
                html.Li("Constraints might contradict each other."),
                html.Li("Check data types (numbers vs text)."),
                html.Li("Check syntax in Advanced View.")
            ], style={'paddingLeft': '20px', 'marginBottom': '15px', 'color': '#555'}),
            html.Code(res.get('error_msg'), style={'backgroundColor': 'rgba(255,255,255,0.7)', 'padding': '10px', 'borderRadius': '4px', 'display': 'block', 'fontSize': '13px', 'fontFamily': 'monospace'})
        ])
        return {'display':'none'}, "Error", {'color':'#dc3545'}, "-", "Error", [], [], {}, {'display':'none'}, "", friendly_error, error_style, {'display':'block'}, current_tab
    
    fig = {}
    table_rows = []
    insight = "Optimization complete."
    obj_label = "Total Cost ($)" if sense == 'minimize' else "Total Profit ($)"
    constraints_display = {'flex': 1} 

    # [CHANGED] Use 'analytics' module result processing
    if mode == 'cutting':
        constraints_display = {'display': 'none'}
        fig, table_rows = cut_analytics.process_results(res, store)
        insight = f"### ✅ Optimized: {obj_label}: ${res['objective']:,.2f}\n- **Used Stocks:** {len(table_rows)} EA"
    else:
        table_rows = [{'Stock': v['Variable'], 'Plan': '-', 'Usage': v['Value']} for v in res['variables'] if v['Value'] > 0]
        df = pd.DataFrame(res['variables'])
        df = df[df['Value'] > 0]
        if not df.empty:
            fig = px.bar(df, x='Variable', y='Value', title='Optimization Results')

    status_style = {'color':'#333'}
    insight_style = {'display':'block', 'backgroundColor': '#e3f2fd', 'padding': '25px', 'borderRadius': '12px', 'marginBottom': '40px', 'marginTop': '20px'}
    
    return {'display':'block'}, res['status'], status_style, f"${res['objective']:,.2f}", obj_label, table_rows, res['constraints'], fig, insight_style, insight, "", {'display':'none'}, constraints_display, "tab-3"

if __name__ == '__main__':
    app.run_server(debug=True)
