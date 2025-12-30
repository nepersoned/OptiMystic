# common/styles.py

# --- Table Container Style ---
TABLE_CONTAINER_STYLE = {
    'borderRadius': '4px', 'overflow': 'hidden', 
    'border': '1px solid #d1d1d1', 'marginBottom': '15px'
}

# --- Table Header Style ---
TABLE_HEADER_STYLE = {
    'backgroundColor': '#eef1f6', 'color': '#333', 'fontWeight': 'bold', 
    'textAlign': 'center', 'padding': '10px 5px', 'border': '1px solid #c0c0c0', 
    'fontSize': '13px'
}

# --- Table Cell Style ---
TABLE_CELL_STYLE = {
    'padding': '8px 10px', 'border': '1px solid #e0e0e0', 
    'fontSize': '13px', 'fontFamily': 'Inter, sans-serif', 
    'textAlign': 'left', 'color': '#333', 'minWidth': '80px'
}

# --- Conditional Styles (Stripes, Selection) ---
TABLE_CONDITIONAL_STYLE = [
    {'if': {'row_index': 'odd'}, 'backgroundColor': '#fff'},
    
    # Active/Selected Cell Styling (Blue Border)
    {
        'if': {'state': 'active'}, 
        'backgroundColor': '#e8f0fe', 
        'border': '2px solid #1a73e8 !important', 
        'color': '#1967d2'
    },
    {
        'if': {'state': 'selected'}, 
        'backgroundColor': '#e8f0fe', 
        'border': '2px solid #1a73e8 !important',
        'color': '#1967d2'
    }
]

# --- CSS Hacks for Dash Table ---
FIXED_CSS = [
    {'selector': '.dash-cell', 'rule': 'text-align: left !important;'}, 
    {'selector': '.dash-header', 'rule': 'text-align: center !important;'},
    {'selector': '.dash-cell input', 'rule': 'text-align: left !important;'},
    {'selector': '.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td.focused', 
     'rule': 'box-shadow: inset 0 0 0 2px #1a73e8 !important; outline: none !important; border: 2px solid #1a73e8 !important;'}
]

# --- Button Styles ---
ADD_BTN_STYLE = {
    'width': '100%', 'padding': '12px', 'border': '2px dashed #dee2e6', 
    'borderRadius': '8px', 'backgroundColor': 'transparent', 'color': '#007bff', 
    'fontWeight': '600', 'fontSize': '14px', 'cursor': 'pointer'
}

PRIMARY_BTN_STYLE = {
    'width': '100%', 'padding': '16px', 'backgroundColor': '#4a4e69', 
    'color': 'white', 'fontSize': '16px', 'marginTop': '0', 
    'boxShadow': '0 4px 12px rgba(74, 78, 105, 0.3)', 'border': 'none', 
    'borderRadius': '8px', 'cursor': 'pointer', 'fontWeight': '600'
}
