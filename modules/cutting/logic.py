# modules/cutting/logic.py

def bridge_cutting(params):
    """
    Generates the mathematical model (Objective & Constraints) for Cutting Stock.
    """
    items = params.get('Items', [])
    item_lens = params.get('ItemLens', [])
    demands = params.get('Demands', {})
    prices = params.get('Prices', {})
    stocks = params.get('Stocks', [{'Name': 'Default', 'Length': 1000, 'Cost': 1, 'Limit': 999}])
    sense = params.get('Sense', 'minimize') # 'minimize' or 'maximize'
    
    variables = []
    constraints = []
    obj_terms = []
    
    # Calculate rough upper bound for bins
    total_req_len = sum(demands.get(i, 0) * l for i, l in zip(items, item_lens))
    
    # Iterate Stocks
    for s_idx, stock in enumerate(stocks):
        s_len = stock['Length']
        s_cost = stock['Cost']
        s_limit = int(stock['Limit'])
        
        # Heuristic for max bins
        max_bins = min(s_limit, int((total_req_len / s_len) * 1.5) + 2)
        
        for b_idx in range(max_bins):
            # Bin Used Variable (Binary)
            v_name = f"U_ST{s_idx}_B{b_idx}"
            variables.append({'name': v_name, 'shape': 'scalar', 'type': 'Binary', 'data': 0})
            
            # Objective Term
            if sense == 'minimize':
                obj_terms.append(f"{s_cost} * {v_name}")
            else:
                obj_terms.append(f"-{s_cost} * {v_name}") # Subtract cost from profit
            
            # Assignment Variables (Integer)
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

    # C2. Demand Constraint
    for i_idx, item in enumerate(items):
        all_assigns = [v['name'] for v in variables if f"A_IT{i_idx}_" in v['name']]
        lhs = " + ".join(all_assigns)
        req_qty = demands.get(item, 0)
        
        if sense == 'minimize':
            # Min Cost: MUST meet demand
            constraints.append(f"{lhs} >= {req_qty}")
        else:
            # Max Profit: CAN sell up to demand
            constraints.append(f"{lhs} <= {req_qty}")

    obj_str = " + ".join(obj_terms) if obj_terms else "0"
    
    return obj_str, "\n".join(constraints), variables
