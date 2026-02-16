# app.py
import dash
from dash import html, dcc, dash_table
import analytics_cutting as cut_analytics
import global_callbacks 
from styles import *

# Inject FIXED_CSS as a single CSS string to ensure global styles apply immediately
def _build_fixed_css():
    css_rules = []
    for r in FIXED_CSS:
        sel = r.get('selector', '')
        rule = r.get('rule', '')
        css_rules.append(f"{sel} {{ {rule} }}")
    return "\n".join(css_rules)

_GLOBAL_CSS = _build_fixed_css()

app = dash.Dash(
    __name__, 
    external_stylesheets=['https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap'], 
    title='OptiMystic Cutting Pro', 
    suppress_callback_exceptions=True
)

app.index_string = '''<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>''' + _GLOBAL_CSS + '''</style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>'''

app.layout = html.Div([
    dcc.Store(id='all-data-store', data={}),
    html.Div([
        # Main Header
        html.Div([
            html.Div([
                html.H2("✂️ OptiMystic Cutting Pro", style=HEADER_TITLE_STYLE),
                html.P("AI-Powered Cutting Optimization & Analysis", style={'color': '#cbd5e1', 'margin': '8px 0 0 0', 'fontSize': '13px', 'fontWeight': '500'})
            ], style={'display': 'flex', 'flexDirection': 'column'})
        ], style=HEADER_STYLE),
        
        dcc.Tabs(id='main-tabs', value='tab-1', children=[
            # TAB 1: Inputs
            dcc.Tab(label='1. INPUT PARAMETERS', value='tab-1', children=[
                html.Div(cut_analytics.render_input(), style=SECTION_CONTAINER_STYLE)
            ]),
            
            # TAB 2: Strategy
            dcc.Tab(label='2. OPTIMIZATION STRATEGY', value='tab-2', children=[
                html.Div([
                    html.Div([
                        html.H4("⚙️ Solver Configuration", style={'fontWeight':'800', 'marginBottom':'25px'}),
                        dcc.RadioItems(
                            id='solver-sense', 
                            options=[
                                {'label': ' 📉 Minimize Waste & Cost', 'value': 'minimize'}, 
                                {'label': ' 💰 Maximize Revenue', 'value': 'maximize'}
                            ], value='minimize', labelStyle={'display': 'block', 'marginBottom': '15px', 'fontSize':'16px'}
                        ),
                        html.Button("🚀 EXECUTE OPTIMIZATION", id='btn-solve', n_clicks=0, style=PRIMARY_BTN_STYLE)
                    ], style=CARD_STYLE, className='card-hover')
                ], style=SECTION_CONTAINER_STYLE)
            ]),
            
            # TAB 3: Plan
            dcc.Tab(label='3. OPTIMAL PLAN', value='tab-3', children=[
                html.Div([
                    html.Div(id='results-placeholder', children=[html.H3("Waiting for Input...", style={'textAlign':'center', 'padding':'100px', 'color': NEUTRAL_300})]),
                    html.Div(id='result-dashboard', style={'display': 'none'}, children=[
                        html.Div([
                            html.Div([html.P("SOLVER STATUS", style={'fontSize':'12px', 'fontWeight':'800', 'color':'#94a3b8'}), html.H2(id='res-status', style={'margin':0, 'fontWeight':'800', 'color': NEUTRAL_900})], style=CARD_STYLE, className='card-hover'),
                            html.Div([html.P("OPTIMAL OBJECTIVE", style={'fontSize':'12px', 'fontWeight':'800', 'color':'#94a3b8'}), html.H2(id='res-objective', style={'margin':0, 'fontWeight':'800', 'color': PRIMARY_COLOR})], style=CARD_STYLE, className='card-hover')
                        ], style={'display': 'flex', 'gap': '20px', 'flexWrap': 'wrap'}),
                        html.Div(id='res-insight-area', children=[dcc.Loading(type='circle', children=[dcc.Markdown(id='res-insight-text')])], style=INSIGHT_BOX_STYLE),
                        html.Div([dcc.Loading(type='circle', children=[dcc.Graph(id='res-chart')])], style=CARD_STYLE, className='card-hover'),
                        html.Div([dcc.Loading(type='circle', children=[dash_table.DataTable(id='res-table', columns=[{'name':'Stock','id':'Stock'},{'name':'Plan','id':'Plan'},{'name':'Usage','id':'Usage'}], style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE)])], style=CARD_STYLE, className='card-hover')
                    ])
                ], style=SECTION_CONTAINER_STYLE)
            ]),
        ])
    ], className='main-container', style={**MAIN_CONTAINER_STYLE, 'overflow': 'hidden'})
], style={'minHeight': '100vh', 'backgroundColor': NEUTRAL_50, 'display': 'flex', 'justifyContent': 'center', 'padding': SPACING_XL})

global_callbacks.init_callbacks(app)
if __name__ == '__main__':
    app.run(debug=True)