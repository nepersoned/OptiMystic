from dash import html, dash_table, dcc

# --- [Styles] ---
add_btn_style = {
    'width': '100%',
    'padding': '14px',  # Increased padding for easier mobile touch
    'border': '2px dashed #dee2e6', 
    'borderRadius': '8px', 
    'backgroundColor': 'transparent', 
    'color': '#007bff', 
    'fontWeight': '600', 
    'fontSize': '14px', 
    'cursor': 'pointer'
}

# Container style
table_container_style = {
    'borderRadius': '4px', 
    'overflow': 'hidden',
    'border': '1px solid #d1d1d1',
    'marginBottom': '15px',
    'maxWidth': '100%'  # Prevent container from overflowing screen width
}

# Header style (Excel-like gray)
table_header_style = {
    'backgroundColor': '#eef1f6', 
    'color': '#333', 
    'fontWeight': 'bold', 
    'textAlign': 'center', 
    'padding': '10px 5px', 
    'border': '1px solid #c0c0c0', 
    'fontSize': '13px',
    'whiteSpace': 'nowrap'  # Prevent header text wrapping
}

# Cell style (Grid lines)
table_cell_style = {
    'padding': '8px 10px', 
    'border': '1px solid #e0e0e0', 
    'fontSize': '13px', 
    'fontFamily': 'Inter, sans-serif', 
    'textAlign': 'left', 
    'color': '#333', 
    'minWidth': '80px',     # Ensure minimum width for readability
    'maxWidth': '150px',
    'whiteSpace': 'normal'
}

# Conditional Styles (Blue highlight)
table_conditional_style = [
    {'if': {'row_index': 'odd'}, 'backgroundColor': '#fff'},
    
    # Active state (Clicked)
    {
        'if': {'state': 'active'}, 
        'backgroundColor': '#e8f0fe', 
        'border': '2px solid #1a73e8 !important', 
        'color': '#1967d2'
    },
    # Selected state (Focused)
    {
        'if': {'state': 'selected'}, 
        'backgroundColor': '#e8f0fe', 
        'border': '2px solid #1a73e8 !important',
        'color': '#1967d2'
    }
]

# CSS Overrides
fixed_css = [
    # Force left alignment for text
    {'selector': '.dash-cell', 'rule': 'text-align: left !important;'}, 
    {'selector': '.dash-header', 'rule': 'text-align: center !important;'},
    
    # Prevent text jumping to the right in Edit Mode (Input)
    {'selector': '.dash-cell input', 'rule': 'text-align: left !important;'},
    
    # Override Dash's default pink focus border with Blue Box Shadow
    {'selector': '.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td.focused', 
     'rule': 'box-shadow: inset 0 0 0 2px #1a73e8 !important; outline: none !important; border: 2px solid #1a73e8 !important;'}
]

# =========================================================
# 1. UI Rendering Function
# =========================================================
def render():
    return html.Div([
        html.Div([
            html.H4("✂️ Cutting Stock Optimization", style={'color': '#4a4e69', 'fontWeight': '800', 'marginBottom': '5px'}),
            html.P("Minimize material cost or maximize profit.", style={'color': '#666', 'fontSize': '14px', 'marginBottom': '25px'}),
        ]),
        
        # Table 1: Stocks (Wrapped in div for mobile scrolling)
        html.Label("1. Stock Inventory (Stocks)", style={'fontWeight': 'bold', 'color': '#333', 'marginTop': '10px', 'display': 'block', 'marginBottom': '5px'}),
        html.Div([ 
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
                style_table=table_container_style, 
                style_header=table_header_style, 
                style_cell=table_cell_style, 
                style_data_conditional=table_conditional_style, 
                css=fixed_css
            )
        ], style={'maxWidth': '100%', 'overflowX': 'auto'}), # Enable horizontal scroll for mobile
        
        html.Button("＋ Add Stock Type", id='btn-add-stock', n_clicks=0, style={**add_btn_style, 'marginBottom': '25px'}),

        # Table 2: Orders (Wrapped in div for mobile scrolling)
        html.Label("2. Order List (Demand & Price)", style={'fontWeight': 'bold', 'color': '#333', 'marginTop': '10px', 'display': 'block', 'marginBottom': '5px'}),
        html.Div([
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
                style_table=table_container_style, 
                style_header=table_header_style, 
                style_cell=table_cell_style, 
                style_data_conditional=table_conditional_style, 
                css=fixed_css
            )
        ], style={'maxWidth': '100%', 'overflowX': 'auto'}), # Enable horizontal scroll for mobile
        
        html.Button("＋ Add Demand Item", id='btn-add-cut', n_clicks=0, style=add_btn_style)
    ])

# =========================================================
# 2. Logic Processing Function
# =========================================================
def get_params(data_inputs, sense):
    # Safety Check: Handle None inputs
    if not data_inputs:
        data_inputs = {}
        
    cut_data = data_inputs.get('cut_table', []) or []
    stock_data = data_inputs.get('cut_stock_table', []) or []
    
    # 1. Parse Data
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
    
    # 2. Build Parameters dictionary
    params = {
        'Items': items, 'ItemLens': item_lens, 
        'Demands': demands, 'Prices': prices, 
        'Stocks': stocks, 'Sense': sense
    }
    
    # 3. Build Symbol Table List for display
    param_list = [
        {'name': 'ItemLens', 'shape': 'list', 'data': item_lens}, 
        {'name': 'Items', 'shape': 'list', 'data': items}, 
        {'name': 'Stocks', 'shape': 'list', 'data': stocks}, 
        {'name': 'Demands', 'shape': 'dict', 'data': demands}, 
        {'name': 'Prices', 'shape': 'dict', 'data': prices}
    ]
    
    return params, param_list
