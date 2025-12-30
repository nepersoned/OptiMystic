# modules/cutting/analytics.py
from dash import html, dash_table, dcc
import pandas as pd
import plotly.graph_objects as go
from common.styles import *

# --- 1. UI Rendering Function ---
def render_input():
    return html.Div([
        html.Div([
            html.H4("Cutting Stock Analytics", style={'color': '#4a4e69', 'fontWeight': '800', 'marginBottom': '5px'}),
            html.P("Minimize cost or maximize profit.", style={'color': '#888', 'fontSize': '13px', 'marginBottom': '20px'}),
            
            # Input: Blade Width
            html.Div([
                html.Label("Blade Width (mm):", style={'fontWeight': 'bold', 'color': '#333', 'marginRight': '10px'}),
                dcc.Input(
                    id='input-kerf', 
                    type='number', 
                    value=0, 
                    min=0, 
                    step=0.1, 
                    placeholder="0", 
                    style={'width': '80px', 'padding': '6px 10px', 'borderRadius': '4px', 'border': '1px solid #ccc', 'fontSize': '14px'}
                )
            ], style={'marginBottom': '25px', 'display': 'flex', 'alignItems': 'center'})
        ]),
        
        # Table 1: Stocks
        html.Label("1. Stock Inventory", style={'fontWeight': '600', 'color': '#333', 'marginTop': '10px', 'display': 'block', 'marginBottom': '5px'}),
        dash_table.DataTable(
            id='cut-stock-table',
            columns=[
                {'name': 'Name', 'id': 'Name', 'editable': True},
                {'name': 'Length (mm)', 'id': 'Length', 'type': 'numeric', 'editable': True},
                {'name': 'Cost ($)', 'id': 'Cost', 'type': 'numeric', 'editable': True},
                {'name': 'Limit (Qty)', 'id': 'Limit', 'type': 'numeric', 'editable': True}
            ],
            data=[
                {'Name': 'Short_Bar', 'Length': 1500, 'Cost': 10, 'Limit': 100},
                {'Name': 'Long_Bar', 'Length': 5000, 'Cost': 28, 'Limit': 50}
            ],
            row_deletable=True, editable=True, 
            style_table=TABLE_CONTAINER_STYLE, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE, 
            style_data_conditional=TABLE_CONDITIONAL_STYLE, css=FIXED_CSS
        ),
        html.Button("＋ Stock", id='btn-add-stock', n_clicks=0, style={**ADD_BTN_STYLE, 'marginBottom': '25px'}),

        # Table 2: Orders
        html.Label("2. Order List", style={'fontWeight': '600', 'color': '#333', 'marginTop': '10px', 'display': 'block', 'marginBottom': '5px'}),
        dash_table.DataTable(
            id='cut-table',
            columns=[
                {'name': 'Item', 'id': 'Item', 'editable': True},
                {'name': 'Length (mm)', 'id': 'Length', 'type': 'numeric', 'editable': True},
                {'name': 'Demand (Qty)', 'id': 'Demand', 'type': 'numeric', 'editable': True},
                {'name': 'Price ($)', 'id': 'Price', 'type': 'numeric', 'editable': True}
            ],
            data=[
                {'Item': 'Table_Leg', 'Length': 700, 'Demand': 20, 'Price': 15}, 
                {'Item': 'Shelf_Top', 'Length': 2200, 'Demand': 5, 'Price': 50},
                {'Item': 'Coaster', 'Length': 100, 'Demand': 30, 'Price': 5}
            ],
            row_deletable=True, editable=True, 
            style_table=TABLE_CONTAINER_STYLE, style_header=TABLE_HEADER_STYLE, style_cell=TABLE_CELL_STYLE, 
            style_data_conditional=TABLE_CONDITIONAL_STYLE, css=FIXED_CSS
        ),
        html.Button("＋ Item", id='btn-add-cut', n_clicks=0, style=ADD_BTN_STYLE)
    ])

# --- 2. Data Parsing ---
def safe_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == '': return default
        return float(value)
    except: return default

def get_params(data_inputs, sense):
    if not data_inputs: data_inputs = {}
    cut_data = data_inputs.get('cut_table', []) or []
    stock_data = data_inputs.get('cut_stock_table', []) or []
    kerf = safe_float(data_inputs.get('kerf_val', 0), 0.0)
    
    items = []
    item_lens = []
    demands = {}
    prices = {}
    
    for r in cut_data:
        if r.get('Item') and str(r.get('Item')).strip() and r.get('Length') and str(r.get('Length')).strip():
            name = str(r['Item'])
            length = safe_float(r['Length'])
            if length > 0:
                items.append(name)
                item_lens.append(length)
                demands[name] = safe_float(r.get('Demand'), 0)
                prices[name] = safe_float(r.get('Price'), 0)

    stocks = []
    for r in stock_data:
        if r.get('Name') and str(r.get('Name')).strip() and r.get('Length') and str(r.get('Length')).strip():
            stocks.append({
                'Name': str(r['Name']),
                'Length': safe_float(r['Length']),
                'Cost': safe_float(r['Cost']),
                'Limit': safe_float(r.get('Limit'), 999)
            })
    
    # Validation Logic is handled in global_callbacks or visually indicated
    params = {'Items': items, 'ItemLens': item_lens, 'Demands': demands, 'Prices': prices, 'Stocks': stocks, 'Sense': sense, 'Kerf': kerf}
    
    param_list = [
        {'name': 'ItemLens', 'shape': 'list', 'data': item_lens}, 
        {'name': 'Items', 'shape': 'list', 'data': items}, 
        {'name': 'Stocks', 'shape': 'list', 'data': stocks}, 
        {'name': 'Demands', 'shape': 'dict', 'data': demands},
        {'name': 'Prices', 'shape': 'dict', 'data': prices},
        {'name': 'Sense', 'shape': 'scalar', 'data': sense},
        {'name': 'Kerf', 'shape': 'scalar', 'data': kerf}
    ]
    return params, param_list

# --- 3. Result Analytics (Bug Fixed: Rounding) ---
def process_results(res, store):
    params = {p['name']: p['data'] for p in store['parameters']}
    items_list = params.get('Items', [])
    prices = params.get('Prices', {}) 
    stock_info_list = params.get('Stocks', [])
    stock_map = {i: s for i, s in enumerate(stock_info_list)}
    lens_list = params.get('ItemLens', [])
    demands = params.get('Demands', {})
    kerf = params.get('Kerf', 0.0)
    
    produced_counts = {item: 0 for item in items_list}
    total_material_cost = 0  
    total_scrap_value = 0     
    total_kerf_value = 0      
    total_revenue = 0 
    
    raw_bins = {} 
    
    for v in res['variables']:
        if v['Value'] <= 1e-5: continue
        name = v['Variable']
        if "A_IT" in name:
            try:
                parts = name.split('_')
                i_idx = int(parts[1].replace('IT',''))
                s_idx = int(parts[2].replace('ST',''))
                b_idx = int(parts[3].replace('B',''))
                if i_idx >= len(items_list) or s_idx >= len(stock_info_list): continue
                
                # [CRITICAL FIX] Use round() before int() to handle solver precision (e.g. 0.99999 -> 1)
                count = int(round(v['Value']))
                
                item_name = items_list[i_idx]
                length = lens_list[i_idx]
                
                produced_counts[item_name] += count
                total_revenue += (count * prices.get(item_name, 0))
                
                key = (s_idx, b_idx)
                if key not in raw_bins: 
                    raw_bins[key] = {'stock_idx': s_idx, 'items': []}
                
                raw_bins[key]['items'].append({'name': item_name, 'count': count, 'len': length})
            except: continue

    sorted_keys = sorted(raw_bins.keys())
    table_rows = []
    global_counter = 1
    
    traces = {} # For Graph Objects
    def add_trace_data(name, y_cat, length, start_pos, color_group='Product'):
        if name not in traces:
            traces[name] = {'y': [], 'x': [], 'base': [], 'type': color_group}
        traces[name]['y'].append(y_cat)
        traces[name]['x'].append(length)
        traces[name]['base'].append(start_pos)

    for key in sorted_keys:
        b_data = raw_bins[key]
        s_idx = b_data['stock_idx']
        stock_def = stock_map[s_idx]
        y_label = f"Stock #{global_counter}"
        
        flat_items = []
        for item_grp in b_data['items']:
            for _ in range(item_grp['count']):
                flat_items.append(item_grp)
        
        if not flat_items: continue
        
        total_material_cost += stock_def['Cost']
        current_pos = 0
        kerf_len_in_this_bar = 0
        
        # Interleave Logic
        for i, item in enumerate(flat_items):
            add_trace_data(item['name'], y_label, item['len'], current_pos, 'Product')
            current_pos += item['len']
            
            if kerf > 0 and i < len(flat_items) - 1:
                if current_pos + kerf <= stock_def['Length']:
                    add_trace_data('Blade', y_label, kerf, current_pos, 'Blade')
                    current_pos += kerf
                    kerf_len_in_this_bar += kerf

        # [POLISH] Ignore micro-waste (< 0.1mm) to prevent visual artifacts
        waste_len = stock_def['Length'] - current_pos
        if waste_len < 0.1: waste_len = 0
        
        if waste_len > 0:
             add_trace_data('Waste', y_label, waste_len, current_pos, 'Waste')
             scrap_ratio = waste_len / stock_def['Length']
             total_scrap_value += stock_def['Cost'] * scrap_ratio

        if kerf_len_in_this_bar > 0:
            kerf_ratio = kerf_len_in_this_bar / stock_def['Length']
            total_kerf_value += stock_def['Cost'] * kerf_ratio

        cut_str = ", ".join([f"{i['name']} ({i['count']})" for i in b_data['items']])
        usage_pct = (current_pos / stock_def['Length']) * 100
        table_rows.append({'Stock': y_label, 'Plan': f"{stock_def['Name']}: {cut_str}", 'Usage': f"{usage_pct:.1f}%"})
        
        global_counter += 1
        
    fig = go.Figure()
    fixed_colors = {'Waste': '#e0e0e0', 'Blade': '#222222'}
    
    for name, data in traces.items():
        color = fixed_colors.get(name)
        fig.add_trace(go.Bar(
            name=name, y=data['y'], x=data['x'], base=data['base'],
            orientation='h', marker_color=color,
            hovertemplate=f"<b>{name}</b><br>Length: %{{x}} mm<extra></extra>"
        ))

    fig.update_layout(
        title='Cutting Plan', barmode='overlay',
        xaxis_title='Length (mm)', yaxis_title='Stock ID',
        template='plotly_white', height=max(350, len(table_rows) * 40),
        margin=dict(l=40, r=40, t=40, b=40), legend={'traceorder': 'normal'}
    )

    gross_profit = total_revenue - total_material_cost
    total_waste_value = total_scrap_value + total_kerf_value
    
    report_md = "### Financial Summary\n\n"
    report_md += f"* **Revenue:** `${total_revenue:,.2f}`\n"
    report_md += f"* **Cost:** `${total_material_cost:,.2f}`\n"
    report_md += f"* **Profit:** `${gross_profit:,.2f}`\n"
    
    if kerf > 0:
        report_md += f"* **Total Waste:** `${total_waste_value:,.2f}` (Scrap: `${total_scrap_value:,.2f}` + Blade Loss: `${total_kerf_value:,.2f}`)\n"
    else:
        report_md += f"* **Waste:** `${total_waste_value:,.2f}`\n"
    report_md += f"* **Stocks Used:** `{len(table_rows)}`\n\n"

    report_md += "### Production Status\n"
    for item in items_list:
        target = int(demands.get(item, 0))
        actual = produced_counts.get(item, 0)
        
        if actual >= target: status_str = ""
        elif actual == 0: status_str = " -- MISSING"
        else: status_str = f" -- Short: {target-actual}"
            
        report_md += f"* **{item}:** {actual} / {target}{status_str}\n"

    return fig, table_rows, report_md
