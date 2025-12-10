import dash
from dash import html, dash_table, dcc, Input, Output, State
from unit_core import VariableDefinition, parse_table_to_objects, parse_variable_name 

app = dash.Dash(__name__)

@app.callback(
    Output('validation-output', 'children'), 
    [Input('input-table', 'data')]          
)
def validate_input_data(rows): 
    error_messages = []
    
    for i, row in enumerate(rows):
        value = row.get('value')
        var_type = row.get('var_type') 
        var_name = row.get('var_name', 'N/A')

        numerical_value = None
        
        if value is None or str(value).strip() == '':
            error_messages.append(f"❌ 오류: {i+1}번째 행의 '값 (Value)'이 비어 있습니다. (변수명: {row.get('var_name', 'N/A')})")
            continue 

        try:
            numerical_value = float(value)
        except ValueError:
            error_messages.append(f"❌ 오류: {i+1}번째 행의 '값 (Value)' ({value})는 유효한 숫자가 아닙니다. (변수명: {row.get('var_name', 'N/A')})")
            continue

        if var_type == 'Binary':
            if numerical_value != 0.0 and numerical_value != 1.0:
                error_messages.append(f"❌ 오류: {i+1}번째 행의 변수 타입이 '이진형'이므로, '값 (Value)'은 0 또는 1만 가능합니다. (현재 값: {value}, 변수명: {var_name})")
                
    if error_messages:
        return html.Div([html.P("❗ 유효성 검사 실패: 다음 오류를 수정하십시오:", style={'color': 'red', 'fontWeight': 'bold'}),
                         html.Ul([html.Li(msg) for msg in error_messages])])
    else:
        return "✅ 입력 데이터 유효성 검사 완료. 이제 최적화 준비를 할 수 있습니다.
        
@app.callback(
    Output('input-table', 'data'),
    Input('add-row-btn', 'n_clicks'),
    State('input-table', 'data'),
    State('input-table', 'columns')
)
def add_row(n_clicks, rows, columns):
    if n_clicks > 0:
        new_row = {c['id']: '' for c in columns}
        new_row['num_indices'] = 0 # 기본값 0 설정
        rows.append(new_row)
    return rows

@app.callback(
    Output('indexed-data-container', 'children'),
    [Input('input-table', 'data')]
)
def generate_indexed_tables(rows):
    indexed_tables = []
    
    for i, row in enumerate(rows):
        var_name = row.get('var_name', f'Unnamed_{i+1}')
        try:
            num_indices = int(row.get('num_indices', 0))
        except ValueError:
            num_indices = 0 # 유효하지 않은 값이면 0으로 처리

        index_range_str = row.get('index_range', '')
        var_type = row.get('var_type')
        if num_indices >= 1 and var_type not in ['Continuous', 'Integer', 'Binary']:
            
            try:
                ranges = [r.strip() for r in index_range_str.split(',') if r.strip()]
                
                sizes = []
                for r in ranges:
                    if '..' in r:
                        end = int(r.split('..')[-1].strip())
                        start = int(r.split('=')[-1].split('..')[0].strip())
                        sizes.append(end - start + 1)
                    else:
                        sizes.append(1) 
            except Exception:
                continue 

            if len(sizes) == 1:
                columns = [{'name': f'{var_name}[{ranges[0].split("=")[0].strip()}]', 'id': 'value', 'type': 'numeric'}]
                initial_data = [{'value': ''} for _ in range(sizes[0])]
            
            elif len(sizes) >= 2:
                cols_j = sizes[1] 
                col_ids = [f'col_{j}' for j in range(cols_j)]
                
                columns = [{'name': ranges[0].split('=')[0].strip(), 'id': 'row_label', 'editable': False}]
                columns += [{'name': f'{ranges[1].split("=")[0].strip()}={j+1}', 'id': col_id, 'type': 'numeric'} for j, col_id in enumerate(col_ids)]
                
                rows_i = sizes[0]
                initial_data = [{'row_label': f'{ranges[0].split("=")[0].strip()}={i+1}', **{col_id: '' for col_id in col_ids}} for i in range(rows_i)]
            
            else:
                continue
                
            indexed_tables.append(
                html.Div([
                    html.H4(f"데이터 입력: {var_name} ({index_range_str})", 
                            style={'marginTop': '15px', 'marginBottom': '5px'}),
                    dash_table.DataTable(
                        id=f'data-table-{var_name}-{i}',
                        columns=columns,
                        data=initial_data,
                        editable=True,
                        row_deletable=False,
                        style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},
                        style_data_conditional=[
                            {'if': {'column_id': 'row_label'}, 'backgroundColor': 'whitesmoke'}
                        ]
                    )
                ], style={'marginBottom': '20px', 'border': '1px solid #ccc', 'padding': '10px'})
            )

    return indexed_tables

app.layout = html.Div([
    html.H1("🧙‍♂️ OptiMystic Solver", style={'textAlign': 'center'}),
    
    html.Div([
        html.H3("🧪 변수 및 파라미터 정의"),
        dash_table.DataTable(
            id='input-table',
            # ✨ 수정 B: 인덱스 컬럼 추가
            columns=[
                {'name': '변수명', 'id': 'var_name', 'type': 'text'},
                {'name': '인덱스 수', 'id': 'num_indices', 'type': 'numeric', 'format': {'specifier': 'd'}},
                {'name': '인덱스 범위', 'id': 'index_range', 'type': 'text'},
                {'name': '값 (Value)', 'id': 'value', 'type': 'numeric'},         
                {'name': '분자 단위', 'id': 'unit_num'},     
                {'name': '분모 단위', 'id': 'unit_denom'},    
                {'name': '변수 타입', 'id': 'var_type', 'presentation': 'dropdown'}, 
            ],
            data=[{'var_name': 'Example', 'value': 100, 'unit_num': 'kg', 'unit_denom': '1', 'var_type': 'Continuous', 'num_indices': 0, 'index_range': ''}],
            editable=True,
            row_deletable=True,
            dropdown={
                'var_type': {
                    'options': [
                        {'label': '연속형 (Continuous)', 'value': 'Continuous'},
                        {'label': '정수형 (Integer)', 'value': 'Integer'},
                        {'label': '이진형 (Binary)', 'value': 'Binary'},
                        {'label': '상수 (Parameter)', 'value': 'Parameter'} # 파라미터 옵션 추가
                    ]
                }
            }
        ), 
        
        html.Div(id='validation-output', 
                 style={'color': 'red', 'marginTop': '10px', 'fontWeight': 'bold'}), 

        html.Button('새로운 변수 추가 (+)', id='add-row-btn', n_clicks=0, 
                    style={'width': '100%', 'marginTop': '10px'}),
 
        html.Hr(style={'marginTop': '30px'}), 
        html.H3("🔢 인덱싱된 파라미터 값 입력", style={'marginTop': '20px'}),
        html.Div("⬆️ 위 테이블에서 상수(Parameter) 변수를 정의하면 아래에 데이터 입력 표가 생성됩니다.", 
                 style={'marginBottom': '10px', 'color': '#555'}),
        
        html.Div(id='indexed-data-container'), # 여기에 동적 테이블이 들어갑니다.

        html.Hr(style={'marginTop': '30px'}), 
        html.H3("🎯 목적 함수 (Objective Function)", style={'marginTop': '20px'}),
        dcc.Dropdown(
            id='objective-type',
            options=[
                {'label': '최대화 (Maximize)', 'value': 'MAX'},
                {'label': '최소화 (Minimize)', 'value': 'MIN'}
            ],
            value='MIN',
            style={'width': '50%'}
        ),
        dcc.Textarea(
            id='objective-formula',
            placeholder='예: SUM(X[i] * Cost[i])',
            style={'width': '100%', 'height': 100, 'marginTop': '10px'}
        ),

        html.H3("🔒 제약 조건 (Constraints)", style={'marginTop': '30px'}),
        dcc.Textarea(
            id='constraints-formula',
            placeholder='각 제약 조건은 한 줄에 하나씩 입력하십시오.\n예: SUM(X[i,j] for j in 1..10) <= Supply[i]',
            style={'width': '100%', 'height': 200, 'marginTop': '10px'}
        ),
        
        html.Button("🚀 최적화 실행", id='solve-btn', n_clicks=0, 
                    style={'width': '100%', 'marginTop': '20px', 'backgroundColor': '#4CAF50', 'color': 'white', 'fontSize': '18px'})

    ], style={'width': '80%', 'margin': 'auto'}), 
])

if __name__ == '__main__':
    app.run_server(debug=True)
