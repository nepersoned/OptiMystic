# modules/cutting/analytics.py
from dash import html, dash_table, dcc
import pandas as pd
import plotly.express as px
from common.styles import *

# --- 1. UI Rendering Function (Input Screen) ---
def render_input():
    return html.Div([
        html.Div([
            html.H4("✂️ Cutting Stock Analytics", style={'color': '#4a4e69', 'fontWeight': '800', 'marginBottom': '5px'}),
            html.P("Minimize material cost or maximize profit.", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '25px'}),
        ]),
        
        # Table 1: Stocks
        html.Label("1. Stock Inventory (Stocks)", style={'fontWeight': 'bold', 'color': '#333', 'marginTop': '10px', 'display': 'block', 'marginBottom': '5px'}),
        dash_table.DataTable(
            id='cut-stock-table',
            columns=[
                {'name': 'Stock Name', 'id': 'Name', 'editable': True},
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
        html.Button("＋ Add Stock Type", id='btn-add-stock', n_clicks=0, style={**ADD_BTN_STYLE, 'marginBottom': '25px'}),

        # Table 2: Orders
        html.Label("2. Order List (Demand & Price)", style={'fontWeight': 'bold', 'color': '#333', 'marginTop': '10px', 'display': 'block', 'marginBottom': '5px'}),
        dash_table.DataTable(
            id='cut-table',
            columns=[
                {'name': 'Item Name', 'id': 'Item', 'editable': True},
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
        html.Button("＋ Add Demand Item", id='btn-add-cut', n_clicks=0, style=ADD_BTN_STYLE)
    ])

# --- 2. Data Parsing Logic ---
def get_params(data_inputs, sense):
    # Safety Check: Handle None inputs
    if not data_inputs:
        data_inputs = {}
        
    cut_data = data_inputs.get('cut_table', []) or []
    stock_data = data_inputs.get('cut_stock_table', []) or []
    
    # Parse Data
    items = [r['Item'] for r in cut_data if r.get('Item')]
    item_lens = [float(r['Length']) for r in cut_data if r.get('Length')]
    demands = {r['Item']: float(r['Demand']) for r in cut_data if r.get('Item')}
    prices = {r['Item']: float(r.get('Price', 0)) for r in cut_data if r.get('Item')}
    
    stocks = [
        {'Name': r['Name'], 
         'Length': float(r['Length']), 
         'Cost': float(r['Cost']), 
         'Limit': float(r.get('Limit', 999))
        } for r in stock_data if r.get('Name')
    ]
    
    # Build Parameters
    params = {
        'Items': items, 'ItemLens': item_lens, 
        'Demands': demands, 'Prices': prices, 
        'Stocks': stocks, 'Sense': sense
    }
    
    # Build Symbol Table List
    param_list = [
        {'name': 'ItemLens', 'shape': 'list', 'data': item_lens}, 
        {'name': 'Items', 'shape': 'list', 'data': items}, 
        {'name': 'Stocks', 'shape': 'list', 'data': stocks}, 
        {'name': 'Demands', 'shape': 'dict', 'data': demands}, 
        {'name': 'Prices', 'shape': 'dict', 'data': prices}
    ]
    
    return params, param_list

# --- 3. Result Visualization Function ---
def process_results(res, store):
    """
    Parses the solver result and generates the chart and table rows for Cutting Stock.
    """
    params = {p['name']: p['data'] for p in store['parameters']}
    items_list = params.get('Items', [])
    lens_list = params.get('ItemLens', [])
    stock_info_list = params.get('Stocks', [])
    stock_map = {i: s for i, s in enumerate(stock_info_list)}
    
    raw_bins = {} 
    
    # Parse variables to reconstruct bins
    for v in res['variables']:
        if v['Value'] <= 1e-5: continue
        name = v['Variable']
        
        # Check if it is an assignment variable (A_ITx_STy_Bz)
        if "A_IT" in name:
            parts = name.split('_')
            # Format: A, IT0, ST0, B0
            i_idx = int(parts[1].replace('IT',''))
            s_idx = int(parts[2].replace('ST',''))
            b_idx = int(parts[3].replace('B',''))
            
            key = (s_idx, b_idx)
            if key not in raw_bins: 
                raw_bins[key] = {'stock_idx': s_idx, 'items': [], 'used_len': 0}
            
            count = int(v['Value'])
            item_name = items_list[i_idx]
            length = lens_list[i_idx]
            
            raw_bins[key]['items'].append({'name': item_name, 'count': count, 'len': length})
            raw_bins[key]['used_len'] += count * length

    sorted_keys = sorted(raw_bins.keys())
    chart_data = []
    table_rows = []
    global_counter = 1
    
    for key in sorted_keys:
        b_data = raw_bins[key]
        if b_data['used_len'] == 0: continue
        
        s_idx = b_data['stock_idx']
        stock_def = stock_map[s_idx]
        display_id = f"Stock #{global_counter}"
        
        cut_str = ", ".join([f"{i['name']} ({i['count']})" for i in b_data['items']])
        usage_pct = (b_data['used_len'] / stock_def['Length']) * 100
        
        table_rows.append({'Stock': display_id, 'Plan': f"{stock_def['Name']}: {cut_str}", 'Usage': f"{usage_pct:.1f}%"})
        
        current_pos = 0
        for item in b_data['items']:
            for _ in range(item['count']):
                chart_data.append({'Stock': display_id, 'Item': item['name'], 'Length': item['len'], 'Type': 'Product'})
                current_pos += item['len']
        
        # Add Waste
        if current_pos < stock_def['Length']:
            chart_data.append({'Stock': display_id, 'Item': '(Waste)', 'Length': stock_def['Length'] - current_pos, 'Type': 'Waste'})
        
        global_counter += 1
        
    fig = {}
    if chart_data:
        df = pd.DataFrame(chart_data)
        fig = px.bar(df, x='Stock', y='Length', color='Item', 
                     title='Visual Cutting Plan', labels={'Length':'Length (mm)'}, 
                     template='plotly_white', color_discrete_map={'(Waste)':'#e0e0e0'})
        fig.update_layout(margin=dict(l=40, r=40, t=40, b=40), height=350, barmode='stack')
        
    return fig, table_rows
