import pandas as pd

def generate_logic(template_type, params):
    if template_type == 'cutting': return bridge_cutting(params)
    elif template_type == 'transportation': return bridge_transportation(params)
    elif template_type == 'prod_mix': return bridge_product_mix(params)
    elif template_type == 'blending': return bridge_blending(params)
    return "", "", []

# ---------------------------------------------------------
# [ULTIMATE] Multi-Stock + Profit/Cost Switching Bridge
# ---------------------------------------------------------
def bridge_cutting(params):
    items = params.get('Items', [])
    item_lens = params.get('ItemLens', [])
    demands = params.get('Demands', {})
    prices = params.get('Prices', {})
    stocks = params.get('Stocks', [{'Name': 'Default', 'Length': 1000, 'Cost': 1, 'Limit': 999}])
    sense = params.get('Sense', 'minimize') # 'minimize' or 'maximize'
    
    variables = []
    constraints = []
    obj_terms = []
    
    total_req_len = sum(demands.get(i, 0) * l for i, l in zip(items, item_lens))
    
    # Iterate Stocks
    for s_idx, stock in enumerate(stocks):
        s_len = stock['Length']
        s_cost = stock['Cost']
        s_limit = int(stock['Limit'])
        
        max_bins = min(s_limit, int((total_req_len / s_len) * 1.5) + 2)
        
        for b_idx in range(max_bins):
            # Bin Used (Binary)
            v_name = f"U_ST{s_idx}_B{b_idx}"
            variables.append({'name': v_name, 'shape': 'scalar', 'type': 'Binary', 'data': 0})
            
            # Objective Term: Cost is always subtracted (negative in profit, positive in cost)
            # Minimize Cost: + Cost * U
            # Maximize Profit: - Cost * U (Revenue - Cost)
            if sense == 'minimize':
                obj_terms.append(f"{s_cost} * {v_name}")
            else:
                obj_terms.append(f"-{s_cost} * {v_name}") # Subtract cost from profit
            
            # Assignments (Integer)
            assign_vars = []
            for i_idx, item in enumerate(items):
                a_name = f"A_IT{i_idx}_ST{s_idx}_B{b_idx}"
                variables.append({'name': a_name, 'shape': 'scalar', 'type': 'Integer', 'data': 0})
                assign_vars.append(a_name)
                
                # Revenue Term (Only for Profit Max)
                if sense == 'maximize':
                    p = prices.get(item, 0)
                    obj_terms.append(f"{p} * {a_name}")

            # C1. Physical Length Constraint
            lhs = " + ".join([f"{a_name} * {item_lens[k]}" for k, a_name in enumerate(assign_vars)])
            constraints.append(f"{lhs} <= {s_len} * {v_name}")

    # C2. Demand Constraint (The Switch)
    for i_idx, item in enumerate(items):
        all_assigns = [v['name'] for v in variables if f"A_IT{i_idx}_" in v['name']]
        lhs = " + ".join(all_assigns)
        req_qty = demands.get(item, 0)
        
        if sense == 'minimize':
            # Min Cost: MUST meet demand (at least)
            constraints.append(f"{lhs} >= {req_qty}")
        else:
            # Max Profit: CAN sell up to demand (at most)
            # If profitable, solver will maximize up to this limit.
            constraints.append(f"{lhs} <= {req_qty}")

    obj_str = " + ".join(obj_terms) if obj_terms else "0"
    
    return obj_str, "\n".join(constraints), variables

# ---------------------------------------------------------
# Other Bridges (Kept separate)
# ---------------------------------------------------------
def bridge_transportation(params):
    plants = params.get('Plants', [])
    regions = params.get('Regions', [])
    variables = [{'name': 'Ship', 'shape': 'matrix', 'type': 'Continuous', 'data': [{'row_label': p, **{r: 0 for r in regions}} for p in plants]}]
    obj_str = "sum(Ship[p][r] * Cost[p][r] for p in Plants for r in Regions)"
    constraints = []
    for p in plants: constraints.append(f"sum(Ship['{p}'][r] for r in Regions) <= Supply['{p}']")
    for r in regions: constraints.append(f"sum(Ship[p]['{r}'] for p in Plants) >= Demand['{r}']")
    return obj_str, "\n".join(constraints), variables

def bridge_product_mix(params):
    products = params.get('Products', [])
    resources = params.get('Resources', [])
    variables = [{'name': 'Produce', 'shape': 'list', 'type': 'Continuous', 'data': [{'Product': p} for p in products]}]
    obj_str = "sum(Produce[i] * Profit[products[i]] for i in range(len(products)))"
    constraints = []
    for res in resources: constraints.append(f"sum(Produce[i] * Usage['{res}'][products[i]] for i in range(len(products))) <= Capacity['{res}']")
    return obj_str, "\n".join(constraints), variables

def bridge_blending(params):
    ingr = params.get('Ingredients', [])
    variables = [{'name': 'W', 'shape': 'list', 'type': 'Continuous', 'data': [{'Ingr': i} for i in ingr]}]
    obj_str = "sum(W[i] * Cost[ingr[i]] for i in range(len(ingr)))"
    min_a = params.get('min_a', 0)
    min_b = params.get('min_b', 0)
    constraints = [f"sum(W[i] * NutA[ingr[i]] for i in range(len(ingr))) >= {min_a}", f"sum(W[i] * NutB[ingr[i]] for i in range(len(ingr))) >= {min_b}"]
    return obj_str, "\n".join(constraints), variables
