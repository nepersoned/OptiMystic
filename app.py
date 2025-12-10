import dash
from dash import html, dash_table, dcc, Input, Output, State

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("🧙‍♂️ OptiMystic Solver", style={'textAlign': 'center'}),
    
    html.Div([
        html.H3("🧪 변수 및 파라미터 정의"),
        
        dash_table.DataTable(
            id='input-table',
            columns=[
                {'name': '변수명', 'id': 'var_name', 'type': 'text'},
                {'name': '인덱스 수', 'id': 'num_indices', 'type': 'numeric', 'format': {'specifier': 'd'}},
                {'name': '인덱스 범위', 'id': 'index_range', 'type': 'text'},
                {'name': '값 (Value)', 'id': 'value', 'type': 'numeric'},         
                {'name': '분자 단위', 'id': 'unit_num'},     
                {'name': '분모 단위', 'id': 'unit_denom'},    
                {'name': '변수 타입', 'id': 'var_type', 'presentation': 'dropdown'}, 
            ],
            data=[
                {'var_name': 'Budget', 'value': 10000, 'unit_num': 'KRW', 'unit_denom': '1', 'var_type': 'Parameter', 'num_indices': 0, 'index_range': ''},
                {'var_name': 'Production', 'value': '', 'unit_num': 'EA', 'unit_denom': '1', 'var_type': 'Continuous', 'num_indices': 0, 'index_range': ''}
            ],
            editable=True,
            row_deletable=True,
            dropdown={
                'var_type': {
                    'options': [
                        {'label': '연속형 (Continuous)', 'value': 'Continuous'},
                        {'label': '정수형 (Integer)', 'value': 'Integer'},
                        {'label': '이진형 (Binary)', 'value': 'Binary'},
                        {'label': '상수 (Parameter)', 'value': 'Parameter'} 
                    ]
                }
            },
            # 🎨 [Quest 2-3 핵심] 조건부 스타일링: 값을 입력하면 안 되는 상황에서 셀 비활성화
            style_data_conditional=[
                {
                    'if': {
                        'column_id': 'value',
                        'filter_query': '{var_type} != "Parameter"'
                    },
                    'backgroundColor': '#e9ecef',  
                    'color': '#adb5bd',            
                    'pointer-events': 'none'       
                },
                # 조건 2: 'Parameter'지만 인덱스 수(num_indices)가 0보다 큰 경우 -> 값 입력 금지 (상세 테이블 사용 예정)
                {
                    'if': {
                        'column_id': 'value',
                        'filter_query': '{var_type} = "Parameter" && {num_indices} > 0'
                    },
                    'backgroundColor': '#e9ecef', 
                    'color': '#adb5bd',
                    'pointer-events': 'none'       
                }
            ]
        ), 
        
        html.Div(id='validation-output', 
                 style={'marginTop': '10px', 'minHeight': '20px'}), 

        html.Button('새로운 변수 추가 (+)', id='add-row-btn', n_clicks=0, 
                    style={'width': '100%', 'marginTop': '10px'}),
        
        html.Hr(style={'marginTop': '30px'}), 
        
        html.H3("🔢 인덱싱된 파라미터 값 입력 (현재 비활성화)", style={'marginTop': '20px', 'color': '#aaa'}),
        html.Div("-> 인덱스가 있는 파라미터(예: Cost[i])는 추후 상세 테이블에서 입력합니다.", 
                 style={'marginBottom': '10px', 'color': '#555'}),

        html.H3("🎯 목적 함수 (Objective Function)", style={'marginTop': '20px'}),
        dcc.Dropdown(id='objective-type', options=[{'label': '최소화 (MIN)', 'value': 'MIN'}, {'label': '최대화 (MAX)', 'value': 'MAX'}], value='MIN', style={'width': '50%'}),
        dcc.Textarea(id='objective-formula', placeholder='예: SUM(Production[i] * Cost[i])', style={'width': '100%', 'height': 100, 'marginTop': '10px'}),
        
        html.H3("🔒 제약 조건 (Constraints)", style={'marginTop': '30px'}),
        dcc.Textarea(id='constraints-formula', placeholder='각 제약 조건은 한 줄에 하나씩 입력하십시오.', style={'width': '100%', 'height': 200, 'marginTop': '10px'}),
        
        html.Button("🚀 최적화 실행", id='solve-btn', n_clicks=0, 
                    style={'width': '100%', 'marginTop': '20px', 'backgroundColor': '#4CAF50', 'color': 'white', 'fontSize': '18px'})

    ], style={'width': '80%', 'margin': 'auto', 'paddingBottom': '50px'}), 
])

@app.callback(
    Output('validation-output', 'children'), 
    [Input('input-table', 'data')]          
)
def validate_input_data(rows): 
    error_messages = []
    
    if not rows:
        return ""

    for i, row in enumerate(rows):
        value = row.get('value')
        var_name = row.get('var_name', 'N/A')
        var_type = row.get('var_type', 'Continuous')
        num_indices = row.get('num_indices', 0)
        unit_num = row.get('unit_num')
        
        if not var_name or str(var_name).strip() == '':
             error_messages.append(f"❌ {i+1}행 오류: '변수명'이 비어 있습니다.")
             continue

        if not unit_num or str(unit_num).strip() == '':
            error_messages.append(f"⚠️ {i+1}행 경고: 변수 '{var_name}'의 '분자 단위'가 비어 있습니다. (예: kg, m, ea)")

        if var_type == 'Parameter':
            if num_indices == 0: 
                if value is None or str(value).strip() == '':
                    error_messages.append(f"❌ {i+1}행 오류: '{var_name}'은 단일 파라미터이므로 '값 (Value)'이 필수입니다.")
                else:
                    try:
                        float(value)
                    except ValueError:
                        error_messages.append(f"❌ {i+1}행 오류: '{var_name}'의 값 '{value}'은 유효한 숫자가 아닙니다.")

    if error_messages:
        return html.Div([
            html.P("❗ 입력 데이터 확인 필요:", style={'color': 'red', 'fontWeight': 'bold'}),
            html.Ul([html.Li(msg) for msg in error_messages])
        ])
    else:
        return html.Div("✅ 데이터 설정 완료. (모든 유효성 검사 통과)", style={'color': 'green', 'fontWeight': 'bold'})

@app.callback(
    Output('input-table', 'data'),
    Input('add-row-btn', 'n_clicks'),
    State('input-table', 'data'),
    State('input-table', 'columns')
)
def add_row(n_clicks, rows, columns):
    if n_clicks > 0:
        new_row = {c['id']: '' for c in columns}
        new_row['num_indices'] = 0
        new_row['var_type'] = 'Continuous'
        new_row['unit_denom'] = '1'
        rows.append(new_row)
    return rows

if __name__ == '__main__':
    app.run_server(debug=True)
    app.run_server(debug=True)
