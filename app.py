import dash
from dash import html, dash_table, dcc, Input, Output, State

@app.callback(
    Output('validation-output', 'children'), 
    [Input('input-table', 'data')]          
)
def validate_input_data(rows):
    variables, error_report = parse_table_to_objects(rows)
    
    if error_report:
        return html.Div([html.P(msg) for msg in error_report]) 
    
    return "✅ 입력 데이터 유효성 검사 완료. 이제 최적화 준비를 할 수 있습니다."

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("🧙‍♂️ OptiMystic Solver", style={'textAlign': 'center'}),
    
    html.Div([
        dash_table.DataTable(
            id='input-table',

            columns=[
                {'name': '변수명', 'id': 'var_name'},
                {'name': '값 (Value)', 'id': 'value'},
                {'name': '단위 (분자)', 'id': 'unit_num'},
                {'name': '단위 (분모)', 'id': 'unit_denom'},
                {'name': '변수 타입', 'id': 'var_type', 'presentation': 'dropdown'},
            ],

            data=[
                {'var_name': 'Example', 'value': 100, 'unit_num': 'kg', 'unit_denom': '1'}
            ],

            editable=True,
            row_deletable=True,
            dropdown={ # DROPDOWN DEFINITION
        'var_type': {
            'options': [
                {'label': '연속형 (Continuous)', 'value': 'Continuous'},
                {'label': '정수형 (Integer)', 'value': 'Integer'},
                {'label': '이진형 (Binary)', 'value': 'Binary'}
            ]
        }
    }
),
            
        ),

        html.Button('새로운 변수 추가 (+)', id='add-row-btn', n_clicks=0, 
                    style={'width': '100%', 'marginTop': '10px'})

    ], style={'width': '80%', 'margin': 'auto'}),
])

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

if __name__ == '__main__':
    app.run_server(debug=True)
