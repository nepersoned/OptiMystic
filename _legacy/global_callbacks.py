# global_callbacks.py
from dash import Input, Output, State, callback_context, no_update
import solver_engine
import bridge_logic
import analytics_cutting as cut_analytics

def init_callbacks(app):
    # 1. Add Stock Material Row
    @app.callback(
        Output('cut-stock-table', 'data'), 
        Input('btn-add-stock', 'n_clicks'), 
        State('cut-stock-table', 'data'), 
        prevent_initial_call=True
    )
    def add_stock(n, data): 
        return (data or []) + [{'Name': f'ST_{len(data or [])+1}', 'Length': 3000, 'Cost': 100, 'Limit': 500}]

    # 2. Add Order Item Rows (Single & Bulk)
    @app.callback(
        Output('cut-table', 'data'), 
        [Input('btn-add-cut', 'n_clicks'), Input('btn-bulk-add', 'n_clicks')], 
        [State('cut-table', 'data'), State('bulk-count', 'data')], 
        prevent_initial_call=True
    )
    def manage_table(n_add, n_bulk, data, bulk_n):
        ctx = callback_context
        if not ctx.triggered: return no_update
        trig = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trig == 'btn-add-cut': 
            return (data or []) + [{'Item': f'Item_{len(data or [])+1}', 'Length': 1200, 'Demand': 1, 'Price': 60}]
        elif trig == 'btn-bulk-add': 
            count = bulk_n if bulk_n else 1
            return (data or []) + [{'Item': f'Item_{len(data or [])+1}', 'Length': 600, 'Demand': 1, 'Price': 30} for _ in range(count)]
        return no_update

    # 2b. Bulk stepper controls: increment / decrement stored count
    @app.callback(
        [Output('bulk-count', 'data'), Output('bulk-count-display', 'children')],
        [Input('bulk-incr', 'n_clicks'), Input('bulk-decr', 'n_clicks')],
        [State('bulk-count', 'data')],
        prevent_initial_call=True
    )
    def update_bulk_count(n_incr, n_decr, current):
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        trig = ctx.triggered[0]['prop_id'].split('.')[0]
        current = int(current or 1)
        if trig == 'bulk-incr':
            current = min(500, current + 1)
        elif trig == 'bulk-decr':
            current = max(1, current - 1)
        return current, str(current)

    # 3. Logic Sync (Pre-Solver Preparation)
    @app.callback(
        Output('all-data-store', 'data', allow_duplicate=True),
        [Input('cut-table', 'data'), Input('cut-stock-table', 'data'), Input('input-kerf', 'value'), Input('solver-sense', 'value')],
        prevent_initial_call=True
    )
    def sync_logic(cut_data, stock_data, kerf, sense):
        inputs = {'cut_table': cut_data, 'cut_stock_table': stock_data, 'kerf_val': kerf}
        params, param_list = cut_analytics.get_params(inputs, sense)
        obj, const, vars_config = bridge_logic.generate_logic('cutting', params)
        # Store a dict (not a single-element list) so downstream callbacks
        # receive a mapping with keys: 'variables', 'parameters', 'obj_str', 'const_str'
        return {'variables': vars_config, 'parameters': param_list, 'obj_str': obj, 'const_str': const}

    # 4. Final Solver Execution & UX Flow
    @app.callback(
        [
            Output('results-placeholder', 'style'),
            Output('result-dashboard', 'style'),
            Output('res-status', 'children'),
            Output('res-objective', 'children'),
            Output('res-table', 'data'),
            Output('res-chart', 'figure'),
            Output('res-insight-text', 'children'),
            Output('main-tabs', 'value') # Automatic tab switch
        ],
        [Input('btn-solve', 'n_clicks')],
        [State('solver-sense', 'value'), State('all-data-store', 'data')]
    )
    def run_solver(n, sense, store):
        if n == 0 or not store: return no_update

        hide, show = {'display': 'none'}, {'display': 'block'}

        # Invoke Core Solver
        res = solver_engine.solve_model(store, sense, store.get('obj_str', ""), store.get('const_str', ""))

        if res.get('status') in ['Infeasible', 'Error']:
            return (show, hide, "Optimization Failed", "-", [], {}, "Error in calculation", 'tab-2')

        # Process Visuals for Results
        fig, rows, report, val = cut_analytics.process_results(res, store)

        # Do not set a success badge in the solver-status area (Tab 2)
        return (
            hide, show, # Reveal result dashboard
            f"Status: {res['status']}",
            f"${val:,.2f}",
            rows,
            fig,
            report,
            'tab-3' # Automatic jump to results
        )