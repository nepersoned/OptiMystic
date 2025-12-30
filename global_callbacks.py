# global_callbacks.py
from dash import Input, Output, State, callback_context, no_update, dcc, html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import solver_engine
import bridge_logic
import modules.cutting.analytics as cut_analytics
from common.styles import *

def init_callbacks(app):
    print("   - [System] Global Callbacks Initialized")

    # --- 1. Add Row Callbacks (단순 행 추가 기능들) ---
    @app.callback(Output('cut-stock-table', 'data'), Input('btn-add-stock', 'n_clicks'), State('cut-stock-table', 'data'), prevent_initial_call=True)
    def add_stock_row(n, data): return (data or []) + [{'Name': f'Stock_{len(data or [])+1}', 'Length': 5000, 'Cost': 50, 'Limit': 100}]

    @app.callback(Output('cut-table', 'data'), Input('btn-add-cut', 'n_clicks'), State('cut-table', 'data'), prevent_initial_call=True)
    def add_cut_row(n, data): return (data or []) + [{'Item': f'Item_{len(data or [])+1}', 'Length': 100, 'Demand': 10, 'Price': 20}]

    @app.callback(Output('pack-table', 'data'), Input('btn-add-pack', 'n_clicks'), State('pack-table', 'data'), prevent_initial_call=True)
    def add_pack_row(n, data): return (data or []) + [{'Item': f'Item_{len(data or [])+1}', 'Weight': 10, 'Value': 100}]

    @app.callback(Output('blend-table', 'data'), Input('btn-add-blend', 'n_clicks'), State('blend-table', 'data'), prevent_initial_call=True)
    def add_blend_row(n, data): return (data or []) + [{'Ingr': f'Ingr_{len(data or [])+1}', 'Cost': 1, 'NutA': 0, 'NutB': 0}]

    @app.callback(Output('pm-products-table', 'data'), Input('pm-add-prod-btn', 'n_clicks'), State('pm-products-table', 'data'), prevent_initial_call=True)
    def add_prod_row(n, data): return (data or []) + [{'Product': f'Prod_{len(data or [])+1}', 'Profit': 100}]

    @app.callback(Output('trans-supply', 'data'), Input('btn-add-source', 'n_clicks'), State('trans-supply', 'data'), prevent_initial_call=True)
    def add_source_row(n, data): return (data or []) + [{'Src': f'F{len(data or [])+1}', 'Cap': 100}]

    @app.callback(Output('trans-demand', 'data'), Input('btn-add-dest', 'n_clicks'), State('trans-demand', 'data'), prevent_initial_call=True)
    def add_dest_row(n, data): return (data or []) + [{'Dst': f'S{len(data or [])+1}', 'Dem': 100}]

    @app.callback(Output('inv-table', 'data'), Input('btn-add-inv', 'n_clicks'), State('inv-table', 'data'), prevent_initial_call=True)
    def add_inv_row(n, data): return (data or []) + [{'Item': f'Item_{len(data or [])+1}', 'Demand': 100, 'Cost': 10}]

    @app.callback(Output('invest-table', 'data'), Input('btn-add-invest', 'n_clicks'), State('invest-table', 'data'), prevent_initial_call=True)
    def add_invest_row(n, data): return (data or []) + [{'Project': f'Proj_{len(data or [])+1}', 'Cost': 10000, 'Return': 15000}]

    @app.callback(Output('pm-resource-matrix', 'data'), Input('pm-add-res-btn', 'n_clicks'), State('pm-resource-matrix', 'data'), State('pm-resource-matrix', 'columns'), prevent_initial_call=True)
    def add_pm_res_row(n, data, cols): return (data or []) + [{c['id']: (f"Res_{len(data)+1}" if c['id'] == 'resource' else 0) for c in cols}]

    @app.callback(Output('sched-matrix', 'data'), Input('btn-add-staff', 'n_clicks'), State('sched-matrix', 'data'), State('sched-matrix', 'columns'), prevent_initial_call=True)
    def add_sched_staff_row(n, data, cols): return (data or []) + [{c['id']: (f"Staff_{len(data)+1}" if c['id'] == 'staff' else 0) for c in cols}]

    # --- 2. Data Sync Logic (Bridge) ---
    @app.callback(
        [Output('solver-objective', 'value'), Output('solver-constraints', 'value'), Output('all-data-store', 'data')],
        [Input('cut-table', 'data'), Input('cut-stock-table', 'data'), Input('input-kerf', 'value'),
         Input('pack-table', 'data'), Input('blend-table', 'data'), Input('pm-products-table', 'data'), Input('pm-resource-matrix', 'data'), Input('sched-matrix', 'data'), Input('trans-supply', 'data'), Input('trans-demand', 'data'), Input('trans-cost-matrix', 'data'), Input('inv-table', 'data'), Input('invest-table', 'data'),
         Input('solver-sense', 'value'), Input('url', 'pathname')]
    )
    def sync_bridge_data(cut_data, stock_data, kerf_val,
                         pack_data, blend_data, pm_prod, pm_res, sched_data, trans_src, trans_dst, trans_cost, inv_data, invest_data, sense, pathname):
        mode = pathname.strip('/') if pathname else ''
        params = {}
        param_list = []
        
        if mode == 'cutting':
            data_inputs = {'cut_table': cut_data, 'cut_stock_table': stock_data, 'kerf_val': kerf_val}
            params, param_list = cut_analytics.get_params(data_inputs, sense)
        
        elif mode == 'packing':
            if not pack_data: pack_data = []
            items = [r['Item'] for r in pack_data if r.get('Item')]
            weights = {r['Item']: float(r['Weight']) for r in pack_data if r.get('Item')}
            values = {r['Item']: float(r['Value']) for r in pack_data if r.get('Item')}
            params = {'Items': items, 'Weights': weights, 'Values': values, 'Capacity': 100}
            param_list = [{'name':'Weights','shape':'dict','data':weights}, {'name':'Values','shape':'dict','data':values}]
        elif mode == 'blending':
            if not blend_data: blend_data = []
            ingr = [r['Ingr'] for r in blend_data if r.get('Ingr')]
            cost = {r['Ingr']: float(r['Cost']) for r in blend_data if r.get('Ingr')}
            nut_a = {r['Ingr']: float(r['NutA']) for r in blend_data if r.get('Ingr')}
            nut_b = {r['Ingr']: float(r['NutB']) for r in blend_data if r.get('Ingr')}
            params = {'Ingredients': ingr, 'Cost': cost, 'NutA': nut_a, 'NutB': nut_b, 'min_a': 20, 'min_b': 30}
            param_list = [{'name':'Cost','shape':'dict','data':cost}, {'name':'NutA','shape':'dict','data':nut_a}, {'name':'NutB','shape':'dict','data':nut_b}]
        elif mode == 'prod_mix':
            if not pm_prod: pm_prod = []
            products = [r['Product'] for r in pm_prod if r.get('Product')]
            profit = {r['Product']: float(r['Profit']) for r in pm_prod if r.get('Product')}
            params = {'Products': products, 'Profit': profit}
            param_list = [{'name':'Profit', 'shape':'dict', 'data':profit}]
        elif mode == 'transportation':
            if not trans_src: trans_src = []
            if not trans_dst: trans_dst = []
            plants = [r['Src'] for r in trans_src if r.get('Src')]
            regions = [r['Dst'] for r in trans_dst if r.get('Dst')]
            supply = {r['Src']: float(r['Cap']) for r in trans_src if r.get('Src')}
            demand = {r['Dst']: float(r['Dem']) for r in trans_dst if r.get('Dst')}
            params = {'Plants': plants, 'Regions': regions, 'Supply': supply, 'Demand': demand}
            param_list = [{'name':'Supply', 'shape':'dict', 'data':supply}, {'name':'Demand', 'shape':'dict', 'data':demand}]
        elif mode == 'schedule':
            if not sched_data: sched_data = []
            staff = [r['Staff'] for r in sched_data if r.get('Staff')]
            params = {'Staff': staff}
            param_list = []
        elif mode == 'inventory':
            if not inv_data: inv_data = []
            items = [r['Item'] for r in inv_data if r.get('Item')]
            demand = {r['Item']: float(r['Demand']) for r in inv_data if r.get('Item')}
            params = {'Items': items, 'Demand': demand}
            param_list = [{'name':'Demand', 'shape':'dict', 'data':demand}]
        elif mode == 'investment':
            if not invest_data: invest_data = []
            projects = [r['Project'] for r in invest_data if r.get('Project')]
            cost = {r['Project']: float(r['Cost']) for r in invest_data if r.get('Project')}
            ret = {r['Project']: float(r['Return']) for r in invest_data if r.get('Project')}
            params = {'Projects': projects, 'Cost': cost, 'Return': ret, 'Budget': 100000}
            param_list = [{'name':'Cost', 'shape':'dict', 'data':cost}, {'name':'Return', 'shape':'dict', 'data':ret}]

        obj, const, vars_config = bridge_logic.generate_logic(mode, params)
        return obj, const, {'variables': vars_config, 'parameters': param_list}

    # --- 3. Run Solver Logic ---
    @app.callback(
        [Output('result-dashboard', 'style'), Output('res-status', 'children'), Output('res-status', 'style'), 
         Output('res-objective', 'children'), Output('res-obj-label', 'children'),
         Output('res-table', 'data'), Output('res-constraints-table', 'data'), Output('res-chart', 'figure'), Output('res-insight-card', 'style'), Output('res-insight-text', 'children'), Output('solver-error-msg', 'children'), Output('solver-error-msg', 'style'), Output('constraints-wrapper', 'style'), Output('main-tabs', 'value')],
        [Input('btn-solve', 'n_clicks')],
        [State('solver-sense', 'value'), State('solver-objective', 'value'), State('solver-constraints', 'value'), State('all-data-store', 'data'), State('main-tabs', 'value'), State('url', 'pathname')]
    )
    def run_solver(n, sense, obj, const, store, current_tab, pathname):
        if n == 0 or not obj: return {'display':'none'}, "-", {}, "-", "Total Objective", [], [], {}, {'display':'none'}, "", "", {'display':'none'}, {'display':'block'}, no_update
        
        # Validation Logic
        params_dict = {p['name']: p['data'] for p in store['parameters']}
        if 'Kerf' in params_dict and 'Stocks' in params_dict:
            kerf = params_dict['Kerf']
            stocks = params_dict['Stocks']
            if stocks and kerf > 0:
                max_stock = max([s['Length'] for s in stocks])
                if kerf >= max_stock:
                    error_msg = f"❌ **Critical Error:**\nBlade Width ({kerf} mm) is larger than your longest stock ({max_stock} mm).\n\nPlease reduce the blade width."
                    error_style = {'display':'block', 'color': '#a94442', 'backgroundColor': '#f2dede', 'border': '1px solid #ebccd1', 'borderRadius': '12px', 'padding': '25px', 'whiteSpace': 'pre-wrap', 'fontWeight': 'bold', 'marginTop': '30px'}
                    return {'display':'none'}, "Error", {'color':'#a94442'}, "-", "Error", [], [], {}, {'display':'none'}, "", dcc.Markdown(error_msg), error_style, {'display':'none'}, "tab-3"

        mode = pathname.strip('/') if pathname else ''
        res = solver_engine.solve_model(store, sense, obj, const)
        
        if res.get('status') == 'Infeasible':
             blue_alert_style = {'display':'block', 'backgroundColor': '#e3f2fd', 'border': '1px solid #b6d4fe', 'borderRadius': '12px', 'padding': '25px', 'whiteSpace': 'pre-wrap', 'fontWeight': '500', 'marginBottom': '30px', 'marginTop': '30px', 'color': '#084298'}
             friendly_error = dcc.Markdown(res.get('error_msg')) 
             return {'display':'none'}, "Infeasible", {'color':'#a94442'}, "-", "Error", [], [], {}, {'display':'none'}, "", friendly_error, blue_alert_style, {'display':'block'}, "tab-3"

        if res.get('status') == 'Error':
            error_style = {'display':'block', 'color': '#c0392b', 'backgroundColor': '#fceae9', 'border': '1px solid #f5c6cb', 'borderRadius': '12px', 'padding': '25px', 'whiteSpace': 'pre-wrap', 'fontWeight': '500', 'marginBottom': '30px', 'marginTop': '30px'}
            friendly_error = html.Code(res.get('error_msg'), style={'backgroundColor': 'rgba(255,255,255,0.7)', 'padding': '10px', 'borderRadius': '4px', 'display': 'block', 'fontSize': '13px', 'fontFamily': 'monospace'})
            return {'display':'none'}, "Error", {'color':'#dc3545'}, "-", "Error", [], [], {}, {'display':'none'}, "", friendly_error, error_style, {'display':'block'}, "tab-3"
        
        fig = {}
        table_rows = []
        insight = "Optimization complete."
        obj_label = "Total Cost ($)" if sense == 'minimize' else "Total Profit ($)"
        constraints_display = {'flex': 1} 

        if mode == 'cutting':
            constraints_display = {'display': 'none'}
            fig, table_rows, insight = cut_analytics.process_results(res, store)
        else:
            table_rows = [{'Stock': v['Variable'], 'Plan': '-', 'Usage': v['Value']} for v in res['variables'] if v['Value'] > 0]
            df = pd.DataFrame(res['variables'])
            df = df[df['Value'] > 0]
            if not df.empty:
                fig = px.bar(df, x='Variable', y='Value', title='Optimization Results')

        status_style = {'color':'#333'}
        insight_style = {'display':'block', 'backgroundColor': '#e3f2fd', 'padding': '25px', 'borderRadius': '12px', 'marginBottom': '40px', 'marginTop': '20px'}
        
        return {'display':'block'}, res['status'], status_style, f"${res['objective']:,.2f}", obj_label, table_rows, res['constraints'], fig, insight_style, insight, "", {'display':'none'}, constraints_display, "tab-3"
