import dash
from dash import html, dash_table, dcc, Input, Output, State, ALL, ctx

app = dash.Dash(__name__)

question_style = {
    'padding': '15px',
    'backgroundColor': '#f8f9fa',
    'borderRadius': '10px',
    'marginBottom': '20px',
    'border': '1px solid #ddd'
}

input_style = {'width': '100%', 'marginBottom': '10px'}

var_columns = [
    {'name': '변수명', 'id': 'var_name', 'type': 'text'},
    {'name': '타입', 'id': 'var_type', 'presentation': 'dropdown'},
    {'name': '인덱스 수', 'id': 'num_indices', 'type': 'numeric'},
    {'name': '인덱스 범위', 'id': 'index_range', 'type': 'text'},
    {'name': '단위', 'id': 'unit_num'},
]

variable_table = dash_table.DataTable(
    id='var-table',
    columns=var_columns,
    data=[],
    editable=True,
    row_deletable=True,
    style_table={'overflowX': 'auto'},
    dropdown={'var_type': {'options': [{'label': i, 'value': i} for i in ['Continuous', 'Integer', 'Binary']]}}
)

param_columns = [
    {'name': '파라미터명', 'id': 'var_name', 'type': 'text'},
    {'name': '값 (Value)', 'id': 'value', 'type': 'numeric'},
    {'name': '인덱스 수', 'id': 'num_indices', 'type': 'numeric'},
    {'name': '인덱스 범위', 'id': 'index_range', 'type': 'text'},
    {'name': '단위', 'id': 'unit_num'},
]

parameter_table = dash_table.DataTable(
    id='param-table',
    columns=param_columns,
    data=[],
    editable=True,
    row_deletable=True,
    style_table={'overflowX': 'auto'},
    style_data_conditional=[{
        'if': {'column_id': 'value', 'filter_query': '{num_indices} > 0'},
        'backgroundColor': '#e9ecef', 'color': 'transparent', 'pointer-events': 'none'
    }]
)

app.layout = html.Div([
    html.H1("OptiMystic: 인덱스 마법사", style={'textAlign': 'center'}),

    html.Div([
        html.H3("Q. 데이터 정의 마법사"),
        
        html.Label("1. 데이터 종류", style={'fontWeight': 'bold'}),
        dcc.RadioItems(
            id='input-category',
            options=[
                {'label': ' 미지수 (Variable)', 'value': 'var'},
                {'label': ' 파라미터 (Parameter)', 'value': 'param'}
            ],
            value='var',
            inline=True,
            style={'marginBottom': '15px'}
        ),

        html.Div([
            html.Div([
                html.Label("2. 이름", style={'fontWeight': 'bold'}),
                dcc.Input(id='input-name', type='text', placeholder='예: Production', style=input_style),
            ], style={'width': '48%', 'display': 'inline-block', 'marginRight': '4%'}),
            html.Div([
                html.Label("3. 단위", style={'fontWeight': 'bold'}),
                dcc.Input(id='input-unit', type='text', placeholder='예: kg', style=input_style),
            ], style={'width': '48%', 'display': 'inline-block'}),
        ]),

        html.Label("4. 인덱스 설정", style={'fontWeight': 'bold', 'marginTop': '10px'}),
        dcc.RadioItems(
            id='input-is-indexed',
            options=[{'label': ' 없음 (Scalar)', 'value': 'no'}, {'label': ' 있음 (Array)', 'value': 'yes'}],
            value='no',
            inline=True
        ),
        
        html.Div(id='index-config-area', children=[
            html.Label("↳ 인덱스 개수 (차원 수)", style={'fontSize': '14px', 'marginTop': '5px'}),
            dcc.Input(id='input-num-indices', type='number', value=1, min=1, max=5, style={'width': '100px', 'marginLeft': '10px'}),
            
            html.Div(id='dynamic-index-inputs', style={'marginTop': '10px', 'padding': '10px', 'backgroundColor': '#eee', 'borderRadius': '5px'})
        ], style={'display': 'none', 'marginBottom': '15px'}),

        html.Div(id='value-input-container', children=[
            html.Label("5. 상수 값 (Value)", style={'fontWeight': 'bold', 'marginTop': '10px'}),
            dcc.Input(id='input-value', type='number', placeholder='숫자 입력', style=input_style)
        ], style={'display': 'none'}),

        html.Div(id='type-input-container', children=[
            html.Label("5. 변수 타입", style={'fontWeight': 'bold', 'marginTop': '10px'}),
            dcc.Dropdown(
                id='input-var-type',
                options=[{'label': i, 'value': i} for i in ['Continuous', 'Integer', 'Binary']],
                value='Continuous',
                style={'marginBottom': '15px'}
            )
        ], style={'display': 'block'}),

        html.Button("추가하기 (Add)", id='submit-btn', n_clicks=0, 
                    style={'width': '100%', 'backgroundColor': '#007bff', 'color': 'white', 'padding': '10px', 'border': 'none', 'borderRadius': '5px', 'marginTop': '10px'})

    ], style=question_style),

    html.Div(id='msg-output', style={'marginBottom': '20px', 'textAlign': 'center', 'fontWeight': 'bold'}),

    dcc.Tabs(id='main-tabs', value='tab-var', children=[
        dcc.Tab(label='결정 변수 목록', value='tab-var', children=[html.Div([variable_table], style={'padding': '20px'})]),
        dcc.Tab(label='파라미터 목록', value='tab-param', children=[html.Div([parameter_table], style={'padding': '20px'})])
    ])

], style={'maxWidth': '900px', 'margin': 'auto', 'padding': '20px'})


@app.callback(
    [Output('index-config-area', 'style'),
     Output('value-input-container', 'style'),
     Output('type-input-container', 'style')],
    [Input('input-category', 'value'),
     Input('input-is-indexed', 'value')]
)
def toggle_visibility(category, is_indexed):
    show = {'display': 'block', 'marginBottom': '10px'}
    hide = {'display': 'none'}

    style_idx = show if is_indexed == 'yes' else hide
    style_val = show if (category == 'param' and is_indexed == 'no') else hide
    style_type = show if category == 'var' else hide

    return style_idx, style_val, style_type

@app.callback(
    Output('dynamic-index-inputs', 'children'),
    Input('input-num-indices', 'value')
)
def render_index_inputs(num):
    if not num or num < 1:
        return []
    
    inputs = []
    for i in range(num):
        inputs.append(html.Div([
            html.Label(f"📌 인덱스 {i+1}의 범위 (예: 1..10 or Seoul,Busan):", style={'fontSize': '12px'}),
            dcc.Input(
                id={'type': 'idx-range-input', 'index': i}, 
                type='text', 
                style={'width': '100%', 'marginBottom': '5px'}
            )
        ]))
    return inputs

@app.callback(
    [Output('var-table', 'data'),
     Output('param-table', 'data'),
     Output('msg-output', 'children'),
     Output('input-name', 'value')],
    Input('submit-btn', 'n_clicks'),
    [State('input-category', 'value'),
     State('input-name', 'value'),
     State('input-unit', 'value'),
     State('input-is-indexed', 'value'),
     State('input-num-indices', 'value'),
     State({'type': 'idx-range-input', 'index': ALL}, 'value'),
     State('input-value', 'value'),
     State('input-var-type', 'value'),
     State('var-table', 'data'),
     State('param-table', 'data')]
)
def add_row(n_clicks, category, name, unit, is_indexed, num_indices, idx_ranges_list, val, var_type, var_rows, param_rows):
    if n_clicks == 0:
        return dash.no_update

    if not name:
        return dash.no_update, dash.no_update, html.Span("이름을 입력하세요!", style={'color': 'red'}), dash.no_update

    if is_indexed == 'yes':
        final_num_indices = num_indices
        valid_ranges = [r for r in idx_ranges_list if r]
        final_range_str = ", ".join(valid_ranges)
    else:
        final_num_indices = 0
        final_range_str = ""
        
    new_row = {
        'var_name': name,
        'unit_num': unit,
        'num_indices': final_num_indices,
        'index_range': final_range_str
    }

    if category == 'param':
        new_row['value'] = val if is_indexed == 'no' else ""
        param_rows.append(new_row)
        return var_rows, param_rows, html.Span(f"✅ 파라미터 '{name}' 추가됨", style={'color': 'green'}), ""
    else:
        new_row['var_type'] = var_type
        var_rows.append(new_row)
        return var_rows, param_rows, html.Span(f"✅ 변수 '{name}' 추가됨", style={'color': 'green'}), ""

if __name__ == '__main__':
    app.run_server(debug=True)
