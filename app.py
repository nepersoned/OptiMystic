import dash
from dash import html, dash_table, dcc, Input, Output, State
app = dash.Dash(__name__)

# ❌ unit_core.py와 관련된 모든 임포트 제거

# --- 콜백 함수 1: validate_input_data 정의 (기본 유효성 검사만 유지) ---
@app.callback(
    Output('validation-output', 'children'), 
    [Input('input-table', 'data')]          
)
def validate_input_data(rows): 
    error_messages = []
    
    for i, row in enumerate(rows):
        value = row.get('value')
        var_name = row.get('var_name', 'N/A')
        
        numerical_value = None
        
        if value is None or str(value).strip() == '':
            error_messages.append(f"❌ 오류: {i+1}번째 행의 '값 (Value)'이 비어 있습니다. (변수명: {row.get('var_name', 'N/A')})")
            continue 

        try:
            # 기본 숫자 변환 유효성 검사만 유지
            numerical_value = float(value)
        except ValueError:
            error_messages.append(f"❌ 오류: {i+1}번째 행의 '값 (Value)' ({value})는 유효한 숫자가 아닙니다. (변수명: {row.get('var_name', 'N/A')})")
            continue 
            
        # ❌ 이진형 검사 및 복잡한 로직은 unit_core 연결 복구 시 재도입 예정
                
    if error_messages:
        return html.Div([html.P("❗ 유효성 검사 실패: 다음 오류를 수정하십시오:", style={'color': 'red', 'fontWeight': 'bold'}),
                         html.Ul([html.Li(msg) for msg in error_messages])])
    else:
        return "✅ 입력 데이터 유효성 검사 완료. 이제 최적화 준비를 할 수 있습니다."

# --- 콜백 함수 2: add_row 정의 (행 추가) ---
@app.callback(
    Output('input-table', 'data'),
    Input('add-row-btn', 'n_clicks'),
    State('input-table', 'data'),
    State('input-table', 'columns')
)
def add_row(n_clicks, rows, columns):
    if n_clicks > 0:
        # 새로 추가되는 행에 인덱스 필드의 기본값을 설정해주는 것이 좋습니다.
        new_row = {c['id']: '' for c in columns}
        new_row['num_indices'] = 0 # 인덱스 수 기본값 0 설정
        rows.append(new_row)
    return rows

# ❌ generate_indexed_tables 콜백 전체 제거

    
# --- 레이아웃 정의 시작 ---
app.layout = html.Div([
    html.H1("🧙‍♂️ OptiMystic Solver", style={'textAlign': 'center'}),
    
    html.Div([
        html.H3("🧪 변수 및 파라미터 정의"),
        dash_table.DataTable(
            id='input-table',
            # ✨ 인덱스 관련 컬럼 복구 (3개)
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
                        {'label': '상수 (Parameter)', 'value': 'Parameter'} 
                    ]
                }
            }
        ), 
        
        html.Div(id='validation-output', 
                 style={'color': 'red', 'marginTop': '10px', 'fontWeight': 'bold'}), 

        html.Button('새로운 변수 추가 (+)', id='add-row-btn', n_clicks=0, 
                    style={'width': '100%', 'marginTop': '10px'}),
        
        # ❌ 인덱싱된 데이터 입력 영역은 현재 비활성화 상태
        html.Hr(style={'marginTop': '30px'}), 
        html.H3("🔢 인덱싱된 파라미터 값 입력 (현재 비활성화)", style={'marginTop': '20px', 'color': '#aaa'}),
        html.Div("-> unit_core 연결 복구 시 동적 테이블 기능이 활성화됩니다.", 
                 style={'marginBottom': '10px', 'color': '#555'}),
        
        # ❌ id='indexed-data-container' 영역은 현재 제거함

        html.H3("🎯 목적 함수 (Objective Function)", style={'marginTop': '20px'}),
        dcc.Dropdown(id='objective-type', options=[], value='MIN', style={'width': '50%'}),
        dcc.Textarea(id='objective-formula', placeholder='예: SUM(X[i] * Cost[i])', style={'width': '100%', 'height': 100, 'marginTop': '10px'}),
        html.H3("🔒 제약 조건 (Constraints)", style={'marginTop': '30px'}),
        dcc.Textarea(id='constraints-formula', placeholder='각 제약 조건은 한 줄에 하나씩 입력하십시오.', style={'width': '100%', 'height': 200, 'marginTop': '10px'}),
        
        html.Button("🚀 최적화 실행", id='solve-btn', n_clicks=0, 
                    style={'width': '100%', 'marginTop': '20px', 'backgroundColor': '#4CAF50', 'color': 'white', 'fontSize': '18px'})

    ], style={'width': '80%', 'margin': 'auto'}), 
])

if __name__ == '__main__':
    app.run_server(debug=True)
