import pulp
import re

def bridge_cutting(params):
    items = params.get('Items', [])
    item_lens = params.get('ItemLens', [])
    demands = params.get('Demands', {})
    prices = params.get('Prices', {})
    stocks = params.get('Stocks', [{'Name': 'Default', 'Length': 1000, 'Cost': 1, 'Limit': 50}])
    sense = params.get('Sense', 'minimize')
    kerf = params.get('Kerf', 0.0)
    
    def clean_name(name):
        return re.sub(r'[^a-zA-Z0-9]', '_', str(name))

    variables = []
    constraints_list = []
    obj_terms = []

    for s_idx, stock in enumerate(stocks):
        stock_len = float(stock['Length'])
        stock_cost = float(stock['Cost'])
        stock_limit = int(stock['Limit'])
        loop_limit = min(stock_limit, 30)

        for b_idx in range(loop_limit):
            bin_id = f"ST{s_idx}_{b_idx}"
            u_var = f"Use_{bin_id}"
            variables.append({'name': u_var, 'type': 'Binary'})
            if sense == 'minimize':
                obj_terms.append({'coef': stock_cost, 'var': u_var})
            else:
                obj_terms.append({'coef': -stock_cost, 'var': u_var})

            assign_vars_for_bin = []
            for i_idx, item in enumerate(items):
                safe_item = clean_name(item)
                a_var = f"Cut_{safe_item}_{bin_id}"
                variables.append({'name': a_var, 'type': 'Integer'})
                if sense == 'maximize':
                    price = float(prices.get(item, 0))
                    obj_terms.append({'coef': price, 'var': a_var})
                eff_len = float(item_lens[i_idx]) + float(kerf)
                assign_vars_for_bin.append({'coef': eff_len, 'var': a_var})

            if assign_vars_for_bin:
                # sum(eff_len * a_var) - (stock_len + kerf) * u_var <= 0
                terms = []
                for t in assign_vars_for_bin:
                    terms.append({'coef': float(t['coef']), 'var': t['var']})
                terms.append({'coef': -float(stock_len + kerf), 'var': u_var})
                constraints_list.append({'type': 'linear', 'terms': terms, 'sense': '<=', 'rhs': 0.0})

    for i_idx, item in enumerate(items):
        safe_item = clean_name(item)
        target = float(demands.get(item, 0))
        my_vars = [v['name'] for v in variables if f"Cut_{safe_item}_" in v['name']]
        if my_vars:
            terms = [{'coef': 1.0, 'var': vn} for vn in my_vars]
            constraints_list.append({'type': 'linear', 'terms': terms, 'sense': '>=', 'rhs': target})

    return obj_terms, constraints_list, variables