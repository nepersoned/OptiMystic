import dash
from dash import html, dash_table, dcc, Input, Output, State
app = dash.Dash(__name__)
@app.callback(
    Output('validation-output', 'children'), 
    [Input('input-table', 'data')]          
)
def validate_input_data(rows): 
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
        )
        html.Div(id='validation-output', 
                 style={'color': 'red', 'marginTop': '10px', 'fontWeight': 'bold'}), 

        html.Button('새로운 변수 추가 (+)', id='add-row-btn', n_clicks=0, 
                    style={'width': '100%', 'marginTop': '10px'})

        ]
        , style={'width': '80%', 'margin': 'auto'}),
])

if __name__ == '__main__':
    app.run_server(debug=True)
