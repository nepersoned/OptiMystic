# analytics_cutting.py
from dash import html, dash_table, dcc
import plotly.graph_objects as go
import plotly.express as px
from styles import *
import re

def safe_float(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def get_params(data_inputs, sense):
    cut_data = data_inputs.get('cut_table', [])
    stock_data = data_inputs.get('cut_stock_table', [])
    kerf = safe_float(data_inputs.get('kerf_val', 0))
    
    items, item_lens, demands, prices = [], [], {}, {}
    for r in cut_data:
        name = str(r.get('Item', '')).strip()
        if name and r.get('Length'):
            items.append(name)
            item_lens.append(safe_float(r['Length']))
            demands[name] = safe_float(r['Demand'])
            prices[name] = safe_float(r.get('Price', 0))
            
    stocks = [{'Name': str(r.get('Name', f"ST_{i}")), 'Length': safe_float(r.get('Length')), 'Cost': safe_float(r.get('Cost', 100)), 'Limit': safe_float(r.get('Limit', 500))} for i, r in enumerate(stock_data) if r.get('Length')]
    
    params = {'Items': items, 'ItemLens': item_lens, 'Demands': demands, 'Prices': prices, 'Stocks': stocks, 'Sense': sense, 'Kerf': kerf}
    param_list = [{'name': k, 'data': v} for k, v in params.items()]
    return params, param_list

def render_input():
    return html.Div([
        # Stock Inventory Section
        html.Div([
            html.Div([
                html.H3("📦 Stock Inventory", style=SECTION_TITLE_STYLE),
                html.P("Configure raw materials and costs", style=SECTION_SUBTITLE_STYLE)
            ], style=SECTION_HEADER_STYLE),
            
                html.Div([
                html.Div([
                    dash_table.DataTable(
                        id='cut-stock-table',
                        columns=[
                            {'name': '📍 Material ID', 'id': 'Name'},
                            {'name': '📏 Length (mm)', 'id': 'Length'},
                            {'name': '💵 Cost ($)', 'id': 'Cost'},
                            {'name': '📊 Qty Limit', 'id': 'Limit'}
                        ],
                        data=[{'Name': 'Standard_Stock', 'Length': 3000, 'Cost': 100, 'Limit': 500}],
                        editable=True,
                        row_deletable=True,
                        style_table=TABLE_CONTAINER_STYLE,
                        style_header=TABLE_HEADER_STYLE,
                        style_cell=TABLE_CELL_STYLE
                    )
                ], style={'marginBottom': SPACING_LG}),

                html.Button("＋ Add New Stock Material", id='btn-add-stock', n_clicks=0, style=ADD_BTN_STYLE),
            ], style=CARD_STYLE, className='card-hover')
        ], style={'marginBottom': SPACING_2XL}),
        
        # Production Orders Section
        html.Div([
            html.Div([
                html.H3("📋 Production Orders", style=SECTION_TITLE_STYLE),
                html.P("Define cutting requirements and demand", style=SECTION_SUBTITLE_STYLE)
            ], style=SECTION_HEADER_STYLE),
            
                html.Div([
                # Kerf + Bulk Add Controls (Top Row)
                html.Div([
                    html.Div([
                        html.Label("✂️ Blade Width (Kerf):", style=INPUT_LABEL_STYLE),
                        html.Div([
                            dcc.Input(id='input-kerf', type='number', value=5, min=0, step=0.1, style={**INPUT_FIELD_STYLE, 'width': '80px', 'textAlign': 'center', 'borderRadius': BORDER_RADIUS_MD}),
                            html.Span("mm", style={'color': NEUTRAL_700, 'marginLeft': SPACING_SM, 'fontWeight': '500', 'fontSize': '13px'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': SPACING_SM})
                    ], style={'flex': 1}),
                    
                    html.Div([
                        html.Label("📦 Bulk Add Items:", style=INPUT_LABEL_STYLE),
                        html.Div([
                            html.Button("-", id='bulk-decr', n_clicks=0, style={**SMALL_BTN_STYLE, 'width':'36px', 'borderRadius': BORDER_RADIUS_MD}),
                            html.Div(id='bulk-count-display', children='1', style={'minWidth':'48px', 'textAlign':'center', 'padding': '6px 10px', 'borderTop':'1px solid '+NEUTRAL_200, 'borderBottom':'1px solid '+NEUTRAL_200}),
                            html.Button("+", id='bulk-incr', n_clicks=0, style={**SMALL_BTN_STYLE, 'width':'36px', 'borderRadius': BORDER_RADIUS_MD}),
                            html.Button("＋ Add Copies", id='btn-bulk-add', n_clicks=0, style={**SMALL_BTN_STYLE, 'marginLeft': SPACING_SM, 'padding': f'{SPACING_SM} {SPACING_MD}'}),
                            dcc.Store(id='bulk-count', data=1)
                            ], style={'display': 'flex', 'alignItems':'center', 'gap': SPACING_SM})
                    ], style={'flex': 1})
                ], style={'display': 'flex', 'gap': SPACING_2XL, 'alignItems': 'flex-end', 'marginBottom': SPACING_2XL, 'padding': f'{SPACING_LG}', 'backgroundColor': LIGHT_BG, 'borderRadius': BORDER_RADIUS_LG}),
                
                # Production Table
                html.Div([
                    dash_table.DataTable(
                        id='cut-table',
                        columns=[
                            {'name': '📝 Item Name', 'id': 'Item'},
                            {'name': '📏 Length (mm)', 'id': 'Length'},
                            {'name': '📦 Demand (pcs)', 'id': 'Demand'},
                            {'name': '💰 Value ($)', 'id': 'Price'}
                        ],
                        data=[
                            {'Item': 'Panel_A', 'Length': 1200, 'Demand': 15, 'Price': 60},
                            {'Item': 'Panel_B', 'Length': 800, 'Demand': 20, 'Price': 30}
                        ],
                        editable=True,
                        row_deletable=True,
                        style_table=TABLE_CONTAINER_STYLE,
                        style_header=TABLE_HEADER_STYLE,
                        style_cell=TABLE_CELL_STYLE
                    )
                ], style={'marginBottom': SPACING_LG}),

                html.Button("＋ Add Item", id='btn-add-cut', n_clicks=0, style=ADD_BTN_STYLE)
            ], style=CARD_STYLE, className='card-hover')
        ])
    ])

def process_results(res, store):
    p = {x['name']: x['data'] for x in store['parameters']}
    items, lens, stocks, kerf = p.get('Items', []), p.get('ItemLens', []), p.get('Stocks', []), p.get('Kerf', 0)
    stock_map = {i: s for i, s in enumerate(stocks)}; raw_bins = {}; total_cost, total_waste = 0, 0
    colors = px.colors.qualitative.Bold; item_colors = {item: colors[i % len(colors)] for i, item in enumerate(items)}
    
    # helper: map cleaned item names to index
    def clean_name_local(name):
        return re.sub(r'[^a-zA-Z0-9]', '_', str(name))
    cleaned_map = {clean_name_local(it): i for i, it in enumerate(items)}

    for v in res['variables']:
        val = v.get('Value', 0.0)
        if val <= 0.001:
            continue

        varname = v['Variable']
        # Case 1: Column-generation naming (A_IT...)
        if "A_IT" in varname:
            try:
                parts = varname.split('_')
                it_part = next(p for p in parts if p.startswith('IT'))
                item_idx = int(it_part.replace('IT', ''))
                bin_id = "_".join(parts[parts.index(it_part)+1:])
                s_idx = int(bin_id.split('_')[0].replace('ST','')) if "ST" in bin_id and "CG" not in bin_id else 0
                if bin_id not in raw_bins: raw_bins[bin_id] = {'s_idx': s_idx, 'items': []}
                for _ in range(int(round(val))): raw_bins[bin_id]['items'].append({'name': items[item_idx], 'len': lens[item_idx]})
            except: 
                continue

        # Case 2: MIP naming from logic_cutting (Cut_<Item>_<Bin>)
        elif varname.startswith('Cut_'):
            try:
                rem = varname[len('Cut_'):]
                # find bin separator (e.g., '_ST')
                pos = rem.rfind('_ST')
                if pos == -1:
                    pos = rem.rfind('_CG')
                if pos == -1:
                    # fallback: split last underscore
                    parts = rem.rsplit('_', 1)
                    item_part = parts[0]
                    bin_id = parts[1] if len(parts) > 1 else 'ST0'
                else:
                    item_part = rem[:pos]
                    bin_id = rem[pos+1:]

                clean_item = clean_name_local(item_part)
                item_idx = cleaned_map.get(clean_item, None)
                if item_idx is None:
                    # try original names
                    try:
                        item_idx = items.index(item_part)
                    except:
                        continue

                s_idx = int(bin_id.split('_')[0].replace('ST','')) if 'ST' in bin_id else 0
                if bin_id not in raw_bins: raw_bins[bin_id] = {'s_idx': s_idx, 'items': []}
                for _ in range(int(round(val))): raw_bins[bin_id]['items'].append({'name': items[item_idx], 'len': lens[item_idx]})
            except:
                continue
            
    fig = go.Figure(); table_rows, legend_tracker = [], set()
    # If no bins/items were produced, return an informative empty figure and report
    if not res or not isinstance(res.get('variables', []), list):
        fig.update_layout(title='No solution produced', template='plotly_white')
        report = "### ℹ️ No cutting plan generated. Please run the solver."
        return fig, [], report, 0.0
    for b_id in sorted(raw_bins.keys()):
        b_data = raw_bins[b_id]; stock = stock_map.get(b_data['s_idx'], stocks[0]); total_cost += stock['Cost']
        current_pos, label = 0, f"Bin {b_id}"
        for i, item in enumerate(b_data['items']):
            show = item['name'] not in legend_tracker; legend_tracker.add(item['name'])
            fig.add_trace(go.Bar(name=item['name'], y=[label], x=[item['len']], base=[current_pos], orientation='h', marker_color=item_colors.get(item['name']), showlegend=show, legendgroup=item['name']))
            current_pos += item['len']
            if kerf > 0 and i < len(b_data['items']) - 1:
                fig.add_trace(go.Bar(name='Blade', y=[label], x=[kerf], base=[current_pos], orientation='h', marker_color='black', showlegend=('Blade' not in legend_tracker), legendgroup='Blade', hoverinfo='skip'))
                legend_tracker.add('Blade'); current_pos += kerf
        waste = max(0, stock['Length'] - current_pos); total_waste += waste
        if waste > 0.1:
            fig.add_trace(go.Bar(name='Waste', y=[label], x=[waste], base=[current_pos], orientation='h', marker={'color': '#e9ecef', 'pattern': {'shape': '/'}}, showlegend=('Waste' not in legend_tracker), legendgroup='Waste'))
            legend_tracker.add('Waste')
        table_rows.append({'Stock': f"{label}", 'Plan': f"{len(b_data['items'])} cut", 'Usage': f"{(current_pos/stock['Length'])*100:.1f}%"})
        
    fig.update_layout(barmode='stack', template='plotly_white', height=max(500, len(raw_bins)*45), margin=dict(t=100, b=50, l=150, r=50), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    # Enhanced report: include totals and top usage summary
    num_bins = len(raw_bins)
    report_lines = [
        "### 📊 Execution Summary",
        f"- **Total Material Cost:** ${total_cost:,.2f}",
        f"- **Total Scrap Generated:** {total_waste:,.1f} mm",
        f"- **Bins Used:** {num_bins}",
        "\n**Top Used Items (sample):**"
    ]
    # summarize top items used across bins
    item_counts = {}
    for b in raw_bins.values():
        for it in b['items']:
            item_counts[it['name']] = item_counts.get(it['name'], 0) + 1
    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for name, cnt in top_items:
        report_lines.append(f"- {name}: {cnt} pcs")
    report = "\n".join(report_lines)
    # ensure types are safe
    return fig, table_rows, report, float(total_cost)

def process_sensitivity(res, store):
    constrs = res.get('constraints', []); p = {x['name']: x['data'] for x in store['parameters']}; items = p['Items']
    if not constrs: return go.Figure(), [], "### 🔍 Strategic Insight\nPlease run Industrial Minimization mode."
    try:
        import pandas as pd
    except Exception as e:
        fig = go.Figure()
        rows = []
        insight = f"### 🔍 Sensitivity analysis unavailable\nFailed to import pandas: {e}"
        return fig, rows, insight

    df = pd.DataFrame(constrs); item_map = {f"C_{i}": items[i] for i in range(len(items))}
    df['Constraint'] = df['Constraint'].map(item_map).fillna(df['Constraint'])
    df = df[df['Constraint'].isin(items)].copy(); df['Impact'] = df['Shadow Price'].abs(); df = df.sort_values(by='Impact', ascending=False)
    fig = go.Figure(go.Bar(x=df['Constraint'], y=df['Shadow Price'], marker_color=['#ff6b6b' if i==0 else '#3b82f6' for i in range(len(df))]))
    fig.update_layout(title="<b>Item Bottleneck Analysis (Marginal Costs)</b>", template='plotly_white')
    top_b = df.iloc[0]['Constraint'] if not df.empty else "N/A"
    top_v = abs(df.iloc[0]['Shadow Price']) if not df.empty else 0
    insight = f"### 🚨 CRITICAL BOTTLENECK: **{top_b}**\n* Adding one more unit of **{top_b}** increases costs by **${top_v:.2f}**.\n* Focus on optimizing this item to reduce overall expenditure."
    rows = df[['Constraint', 'Shadow Price', 'Slack']].to_dict('records')
    for r in rows: r['Shadow Price'] = f"${safe_float(r['Shadow Price']):.2f}"
    return fig, rows, insight