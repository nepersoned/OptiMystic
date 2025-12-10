import dash
from dash import html, dash_table, dcc, Input, Output, State

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
        'if': {'column_id': 'value', 'filter_query': '{index_range} != ""'},
        'backgroundColor': '#e9ecef', 'color': 'transparent', 'pointer-events': 'none'
    }]
)

app.layout = html.Div([
    html.H1("OptiMystic", style={'textAlign': 'center'}),

    html.Div([
        html.H3("Q. 새로운 데이터를 추가해볼까요?"),
        
        html.Label("1. 어떤 종류의 데이터인가요?", style={'fontWeight': 'bold'}),
        dcc.RadioItems(
            id='input-category',
            options=[
                {'label': ' 미지수 (Variable) - 최적화로 구할 값', 'value': 'var'},
                {'label': ' 파라미터 (Parameter) - 이미 알고 있는 상수', 'value': 'param'}
            ],
            value='var',
            inline=True,
            style={'marginBottom': '15px'}
        ),

        html.Div([
            html.Div([
                html.Label("2. 이름이 무엇인가요?", style={'fontWeight': 'bold'}),
                dcc.Input(id='input-name', type='text', placeholder='예: Production, Cost', style=input_style),
            ], style={'width': '48%', 'display': 'inline-block', 'marginRight': '4%'}),
            html.Div([
                html.Label("3. 단위는 무엇인가요?", style={'fontWeight': 'bold'}),
                dcc.Input(id='input-unit', type='text', placeholder='예: kg, EA, KRW', style=input_style),
            ], style={'width': '48%', 'display': 'inline-block'}),
        ]),

        html.Label("4. 인덱스(Index)가 필요한가요? (여러 개입니까?)", style={'fontWeight': 'bold', 'marginTop': '10px'}),
        dcc.RadioItems(
            id='input-is-indexed',
            options=[{'label': ' 아니오 (단일 값)', 'value': 'no'}, {'label': ' 예 (배열/벡터)', 'value': 'yes'}],
            value='no',
            inline=True
        ),
        
        html.Div(id='index-input-container', children=[
            dcc.Input(id='input-index-range', type='text', placeholder='범위를 입력하세요 (예: 1..10 또는 Seoul,Busan)', style={'width': '100%', 'marginTop': '5px'})
        ], style={'display': 'none', 'marginBottom': '15px'}),

        html.Div(id='value-input-container', children=[
            html.Label("5. 값(Value)은 얼마인가요?", style={'fontWeight': 'bold', 'marginTop': '10px'}),
            dcc.Input(id='input-value', type='number', placeholder='숫자만 입력', style=input_style)
        ], style={'display': 'none'}),

        html.Div(id='type-input-container', children=[
            html.Label("5. 변수의 타입은 무엇인가요?", style={'fontWeight': 'bold', 'marginTop': '10px'}),
            dcc.Dropdown(
                id='input-var-type',
                options=[
                    {'label': '연속형 (Continuous)', 'value': 'Continuous'},
                    {'label': '정수형 (Integer)', 'value': 'Integer'},
                    {'label': '이진형 (Binary)', 'value': 'Binary'}
                ],
                value='Continuous',
                style={'marginBottom': '15px'}
            )
        ], style={'display': 'block'}),

        html.Button("추가하기 (Add)", id='submit-btn', n_clicks=0, 
                    style={'width': '100%', 'backgroundColor': '#007bff', 'color': 'white', 'padding': '10px', 'fontSize': '16px', 'border': 'none', 'borderRadius': '5px', 'marginTop': '10px'})

    ], style=question_style),

    html.Div(id='msg-output', style={'marginBottom': '20px', 'textAlign': 'center', 'fontWeight': 'bold'}),

    dcc.Tabs(id='main-tabs', value='tab-var', children=[
        dcc.Tab(label='결정 변수 목록', value='tab-var', children=[
            html.Div([variable_table], style={'padding': '20px'})
        ]),
        dcc.Tab(label='파라미터 목록', value='tab-param', children=[
            html.Div([parameter_table], style={'padding': '20px'})
        ])
    ])

], style={'maxWidth': '900px', 'margin': 'auto', 'padding': '20px'})

@app.callback(
    [Output('index-input-container', 'style'),
     Output('value-input-container', 'style'),
     Output('type-input-container', 'style')],
    [Input('input-category', 'value'),
     Input('input-is-indexed', 'value')]
)
def update_form_visibility(category, is_indexed):
    show = {'display': 'block', 'marginBottom': '10px'}
    hide = {'display': 'none'}

    style_index = show if is_indexed == 'yes' else hide

    if category == 'param' and is_indexed == 'no':
        style_value = show
    else:
        style_value = hide

    style_type = show if category == 'var' else hide

    return style_index, style_value, style_type

@app.callback(
    [Output('var-table', 'data'),
     Output('param-table', 'data'),
     Output('msg-output', 'children'),
     Output('input-name', 'value'), 
     Output('input-value', 'value'),
     Output('input-index-range', 'value')],
    Input('submit-btn', 'n_clicks'),
    [State('input-category', 'value'),
     State('input-name', 'value'),
     State('input-unit', 'value'),
     State('input-is-indexed', 'value'),
     State('input-index-range', 'value'),
     State('input-value', 'value'),
     State('input-var-type', 'value'),
     State('var-table', 'data'),
     State('param-table', 'data')]
)
def add_data(n_clicks, category, name, unit, is_indexed, idx_range, val, var_type, var_rows, param_rows):
    if n_clicks == 0:
        return dash.no_update

    if not name:
        return dash.no_update, dash.no_update, html.Span("이름을 입력해주세요!", style={'color': 'red'}), dash.no_update, dash.no_update, dash.no_update

    new_msg = html.Span(f"'{name}' 추가 완료!", style={'color': 'green'})
    
    final_range = idx_range if is_indexed == 'yes' else ""
    
    if category == 'param':
        final_val = val if is_indexed == 'no' else ""
        
        new_row = {
            'var_name': name,
            'value': final_val,
            'index_range': final_range,
            'unit_num': unit
        }
        param_rows.append(new_row)
        return var_rows, param_rows, new_msg, "", "", ""

    else: 
        new_row = {
            'var_name': name,
            'var_type': var_type,
            'index_range': final_range,
            'unit_num': unit
        }
        var_rows.append(new_row)
        return var_rows, param_rows, new_msg, "", "", ""

if __name__ == '__main__':
    app.run_server(debug=True)
