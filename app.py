import dash
from dash import html, dash_table, dcc, Input, Output, State
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

        if value is None or str(value).strip() == '':
            error_messages.append(f"❌ 오류: {i+1}번째 행의 '값 (Value)'이 비어 있습니다. (변수명: {row.get('var_name', 'N/A')})")
            continue 

        try:
            float(value) 
        except ValueError:
            error_messages.append(f"❌ 오류: {i+1}번째 행의 '값 (Value)' ({value})는 유효한 숫자가 아닙니다. (변수명: {row.get('var_name', 'N/A')})")
            
        if var_type == 'Binary':
            if numerical_value != 0.0 and numerical_value != 1.0:
                error_messages.append(f"❌ 오류: {i+1}번째 행의 변수 타입이 '이진형'이므로, '값 (Value)'은 0 또는 1만 가능합니다. (현재 값: {value}, 변수명: {var_name})")
    if error_messages:
        return html.Div([html.P("❗ 유효성 검사 실패: 다음 오류를 수정하십시오:", style={'color': 'red', 'fontWeight': 'bold'}),
                         html.Ul([html.Li(msg) for msg in error_messages])])
    else:
        return "✅ 입력 데이터 유효성 검사 완료. 이제 최적화 준비를 할 수 있습니다."

@app.callback(
    Output('input-table', 'data'),
    Input('add-row-btn', 'n_clicks'),
    State('input-table', 'data'),
    State('input-table', 'columns')
)
def add_row(n_clicks, rows, columns):
    if n_clicks > 0:
        rows.append({c['id']: '' for c in columns})
    return rows
    
app.layout = html.Div([
    html.H1("🧙‍♂️ OptiMystic Solver", style={'textAlign': 'center'}),
    
    html.Div([
        dash_table.DataTable(
            id='input-table',
            columns=[
                {'name': '변수명', 'id': 'var_name'},
                {'name': '값 (Value)', 'id': 'value'},         
                {'name': '분자 단위', 'id': 'unit_num'},     
                {'name': '분모 단위', 'id': 'unit_denom'},    
                {'name': '변수 타입', 'id': 'var_type', 'presentation': 'dropdown'}, 
            ],
            data=[{'var_name': 'Example', 'value': 100, 'unit_num': 'kg', 'unit_denom': '1', 'var_type': 'Continuous'}],
            editable=True,
            dropdown={
                'var_type': {
                    'options': [
                        {'label': '연속형 (Continuous)', 'value': 'Continuous'},
                        {'label': '정수형 (Integer)', 'value': 'Integer'},
                        {'label': '이진형 (Binary)', 'value': 'Binary'}
                    ]
                }
            }
        ), 
        
        html.Div(id='validation-output', 
                 style={'color': 'red', 'marginTop': '10px', 'fontWeight': 'bold'}), 

        html.Button('새로운 변수 추가 (+)', id='add-row-btn', n_clicks=0, 
                    style={'width': '100%', 'marginTop': '10px'})

    ], style={'width': '80%', 'margin': 'auto'}), 
])

if __name__ == '__main__':
    app.run_server(debug=True)
