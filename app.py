import dash
from dash import html, dash_table, dcc, Input, Output, State, ALL, callback_context
import json
import modules.cutting.analytics as cut_analytics
import global_callbacks # [NEW] Import the new callback manager
from common.styles import *

# --- Server Start ---
print("\n" + "="*50)
print("🚀 OPTIMYSTIC V2.0: MODULAR ARCHITECTURE")
print("   - [Structure] Callbacks moved to 'global_callbacks.py'")
print("   - [Status] System Ready")
print("="*50 + "\n")

external_stylesheets = ['https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, title='OptiMystic Solver', suppress_callback_exceptions=True)
server = app.server

# --- Styles & Layouts ---
app_wrapper_style = {'position': 'fixed', 'top': 0, 'left': 0, 'right': 0, 'bottom': 0, 'backgroundColor': '#eaeff2', 'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'fontFamily': 'Inter, sans-serif'}
main_box_style = {'width': '1280px', 'maxWidth': '96%', 'height': '92vh', 'backgroundColor': 'white', 'borderRadius': '16px', 'boxShadow': '0 20px 60px rgba(0,0,0,0.08)', 'display': 'flex', 'flexDirection': 'column', 'overflow': 'hidden'}
header_style = {'backgroundColor': '#4a4e69', 'padding': '0 30px', 'height': '65px', 'flexShrink': 0, 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'color': 'white'}
content_area_style = {'flex': 1, 'overflowY': 'auto', 'padding': '40px', 'backgroundColor': '#ffffff'}
card_style = {'backgroundColor': 'white', 'borderRadius': '12px', 'padding': '25px', 'border': '1px solid #f1f5f9', 'boxShadow': '0 4px 15px rgba(0, 0, 0, 0.03)', 'textAlign': 'center', 'height': 'auto', 'minHeight': '140px', 'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center', 'transition': 'transform 0.2s'}
tab_selected_style = {'borderTop': '3px solid #4a4e69', 'color': '#4a4e69', 'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'padding': '14px'}
tab_style = {'padding': '14px', 'color': '#888', 'backgroundColor': 'white', 'borderBottom': '1px solid #dee2e6'}

TEMPLATE_GALLERY = [{"id": "cutting", "icon": "✂️", "title": "Cutting Stock", "desc": "Minimize cost or maximize profit."}, {"id": "packing", "icon": "📦", "title": "Bin Packing", "desc": "Load trucks efficiently."}, {"id": "blending", "icon": "🧪", "title": "Blending", "desc": "Optimize mixture recipes."}, {"id": "prod_mix", "icon": "🏭", "title": "Production Mix", "desc": "Maximize profit."}, {"id": "schedule", "icon": "📅", "title": "Scheduling", "desc": "Workforce rostering."}, {"id": "transport", "icon": "🚚", "title": "Transportation", "desc": "Logistics cost min."}, {"id": "inventory", "icon": "📦", "title": "Inventory Opt", "desc": "Prevent stockouts & Reduce costs."}, {"id": "investment", "icon": "💰", "title": "Investment", "desc": "Maximize ROI within budget."}]

# --- Simple Templates (Just for Layout) ---
ui_packing = html.Div([html.H4("📦 Bin Packing"), dash_table.DataTable(id='pack-table', columns=[{'name':'Item','id':'Item'},{'name':'Weight','id':'Weight'},{'name':'Value','id':'Value'}], data=[{'Item': 'Box1', 'Weight': 30, 'Value': 50}], editable=True, row_deletable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add", id='btn-add-pack', style=ADD_BTN_STYLE)])
ui_blending = html.Div([html.H4("🧪 Blending"), dash_table.DataTable(id='blend-table', columns=[{'name':'Ingr','id':'Ingr'},{'name':'Cost','id':'Cost'},{'name':'NutA','id':'NutA'},{'name':'NutB','id':'NutB'}], data=[{'Ingr': 'A', 'Cost': 10, 'NutA': 1, 'NutB': 2}], editable=True, row_deletable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add", id='btn-add-blend', style=ADD_BTN_STYLE)])
ui_prod_mix = html.Div([html.H4("🏭 Production Mix"), dash_table.DataTable(id='pm-products-table', columns=[{'name':'Product','id':'Product'},{'name':'Profit','id':'Profit'}], data=[{'Product': 'P1', 'Profit': 100}], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), dash_table.DataTable(id='pm-resource-matrix', columns=[{'name':'Resource','id':'resource'}, {'name': 'Availability', 'id': 'avail'}], data=[{'resource': 'Labor', 'avail': 100}], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add Prod", id='pm-add-prod-btn', style=ADD_BTN_STYLE), html.Button("Add Res", id='pm-add-res-btn', style=ADD_BTN_STYLE)])
ui_schedule = html.Div([html.H4("📅 Scheduling"), dash_table.DataTable(id='sched-matrix', columns=[{'name':'Staff','id':'staff'}], data=[{'staff': 'Staff1'}], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add", id='btn-add-staff', style=ADD_BTN_STYLE)])
ui_transport = html.Div([html.H4("🚚 Transportation"), dash_table.DataTable(id='trans-supply', columns=[{'name':'Src','id':'Src'}, {'name': 'Cap', 'id': 'Cap'}], data=[{'Src': 'F1', 'Cap': 100}], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), dash_table.DataTable(id='trans-demand', columns=[{'name':'Dst','id':'Dst'}, {'name': 'Dem', 'id': 'Dem'}], data=[{'Dst': 'S1', 'Dem': 50}], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), dash_table.DataTable(id='trans-cost-matrix', columns=[{'name':'Label','id':'label'}], data=[], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add Src", id='btn-add-source', style=ADD_BTN_STYLE), html.Button("Add Dst", id='btn-add-dest', style=ADD_BTN_STYLE)])
ui_inventory = html.Div([html.H4("📦 Inventory"), dash_table.DataTable(id='inv-table', columns=[{'name':'Item','id':'Item'}, {'name': 'Demand', 'id': 'Demand'}, {'name': 'Cost', 'id': 'Cost'}], data=[], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add", id='btn-add-inv', style=ADD_BTN_STYLE)])
ui_investment = html.Div([html.H4("💰 Investment"), dash_table.DataTable(id='invest-table', columns=[{'name':'Project','id':'Project'}, {'name': 'Cost', 'id': 'Cost'}, {'name': 'Return', 'id': 'Return'}], data=[], editable=True, style_table=TABLE_CONTAINER_STYLE, css=FIXED_CSS, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE), html.Button("Add", id='btn-add-invest', style=ADD_BTN_STYLE)])

# --- Modeling & Dashboard ---
modeling_section = html.Div([
    html.Div([html.H4("⚙️ Solver Configuration", style={'color': '#4a4e69', 'fontWeight': '700', 'marginBottom': '8px'}), html.P("Configure how the AI solves your problem.", style={'color': '#888', 'fontSize': '13px'})], style={'marginBottom': '30px'}),
    html.Div([html.Label("Optimization Goal", style={'fontSize': '12px', 'fontWeight': '700', 'textTransform': 'uppercase', 'color': '#888', 'marginBottom': '10px', 'display': 'block', 'letterSpacing': '0.5px'}), dcc.RadioItems(id='solver-sense', options=[{'label': ' Minimize Cost', 'value': 'minimize'}, {'label': ' Maximize Profit', 'value': 'maximize'}], value='minimize', labelStyle={'display': 'block', 'marginBottom': '8px', 'fontWeight': '600', 'color': '#4a4e69', 'cursor': 'pointer'}, inputStyle={'marginRight': '10px'})], style={'backgroundColor': '#f8f9fa', 'padding': '25px', 'borderRadius': '12px', 'marginBottom': '25px', 'border': '1px solid #e9ecef'}),
    html.Details([html.Summary("🔧 Advanced: View/Edit Mathematical Model", style={'cursor': 'pointer', 'fontWeight': '600', 'color': '#007bff', 'fontSize': '14px'}), html.Div([html.Label("Objective Function:", style={'fontWeight': 'bold', 'marginTop': '15px', 'display': 'block', 'fontSize': '13px'}), dcc.Textarea(id='solver-objective', style={'width': '100%', 'height': '80px', 'border': '1px solid #ccc', 'padding': '12px', 'borderRadius': '8px', 'fontFamily': 'monospace', 'backgroundColor': '#fcfcfc', 'marginTop': '5px', 'fontSize': '12px'}), html.Label("Constraints:", style={'fontWeight': 'bold', 'marginTop': '15px', 'display': 'block', 'fontSize': '13px'}), dcc.Textarea(id='solver-constraints', style={'width': '100%', 'height': '150px', 'border': '1px solid #ccc', 'padding': '12px', 'borderRadius': '8px', 'fontFamily': 'monospace', 'backgroundColor': '#fcfcfc', 'marginTop': '5px', 'fontSize': '12px'})], style={'padding': '20px', 'border': '1px solid #eee', 'borderRadius': '12px', 'marginTop': '10px', 'backgroundColor': 'white'})], style={'marginBottom': '30px'}),
    html.Button("🚀 Run Optimization Engine", id='btn-solve', n_clicks=0, style=PRIMARY_BTN_STYLE)
])

dashboard_section = html.Div([
    html.H4("📊 Optimization Results", style={'color': '#4a4e69', 'fontWeight': '700', 'marginBottom': '25px'}),
    html.Div([
        html.Div([
            html.Div([html.H6("Solver Status", style={'margin':0, 'color':'#888', 'fontWeight':'600', 'fontSize': '13px', 'textTransform': 'uppercase'}), html.H3(id='res-status', children="-", style={'margin':'10px 0', 'fontWeight':'800', 'fontSize': '28px', 'color': '#333'})], style=card_style), 
            html.Div([html.H6(id='res-obj-label', children="Total Cost", style={'margin':0, 'color':'#888', 'fontWeight':'600', 'fontSize': '13px', 'textTransform': 'uppercase'}), html.H3(id='res-objective', children="-", style={'margin':'10px 0', 'fontWeight':'800', 'color':'#007bff', 'fontSize': '28px'})], style=card_style),
        ], style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px'}),
        html.Div(id='res-insight-card', style={'backgroundColor': '#e3f2fd', 'padding': '25px', 'borderRadius': '12px', 'display': 'none'}, children=[html.H5("💡 Insight & Report", style={'color': '#0d47a1', 'fontWeight': '700', 'marginTop': 0, 'marginBottom': '10px'}), dcc.Markdown(id='res-insight-text', style={'fontSize': '15px', 'lineHeight': '1.6', 'color': '#0d47a1', 'margin': 0})]),
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

# --- Router & Callback Init ---
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

# [IMPORTANT] Initialize Global Callbacks Here
global_callbacks.init_callbacks(app)

if __name__ == '__main__':
    app.run_server(debug=True)
