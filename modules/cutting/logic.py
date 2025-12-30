# modules/cutting/logic.py
import pulp

def bridge_cutting(params):
    """
    Strict Cutting Stock Logic:
    Accounts for Kerf (Blade Width) occurring ONLY between items (N-1 cuts).
    
    Mathematical Trick:
    Sum( ItemLen + Kerf ) <= StockLen + Kerf
    This mathematically ensures exactly (N-1) kerfs are counted within the limit.
    """
    items = params.get('Items', [])
    item_lens = params.get('ItemLens', [])
    demands = params.get('Demands', {})
    prices = params.get('Prices', {})
    stocks = params.get('Stocks', [{'Name': 'Default', 'Length': 1000, 'Cost': 1, 'Limit': 999}])
    sense = params.get('Sense', 'minimize')
    kerf = params.get('Kerf', 0.0) 
    
    variables = []
    constraints = []
    obj_terms = []
    
    # 1. Effective Lengths
    # We add kerf to EVERY item length for the LHS (Left Hand Side)
    eff_item_lens = [l + kerf for l in item_lens]
    
    for s_idx, stock in enumerate(stocks):
        stock_name = stock['Name']
        stock_len = stock['Length']
        stock_cost = stock['Cost']
        stock_limit = int(stock['Limit'])
        
        # 2. Adjusted Capacity for RHS (Right Hand Side)
        # We give the stock a "bonus" capacity of 1 Kerf.
        # This cancels out the "extra" kerf added to the very last item in the bin.
        # Logic: (Item1+K) + (Item2+K) <= Stock + K  -->  Item1 + K + Item2 <= Stock
        adjusted_stock_len = stock_len + kerf

        for b_idx in range(stock_limit):
            bin_id = f"ST{s_idx}_B{b_idx}"
            
            # Binary Variable: Is this bin used?
            u_var = f"U_{bin_id}"
            variables.append({'name': u_var, 'type': 'Binary'})
            
            # Objective
            if sense == 'minimize':
                obj_terms.append(f"{stock_cost} * {u_var}")
            else:
                obj_terms.append(f"-{stock_cost} * {u_var}")
            
            # Assignment Variables
            assign_vars = []
            for i_idx, item in enumerate(items):
                a_var = f"A_IT{i_idx}_{bin_id}"
                variables.append({'name': a_var, 'type': 'Integer'})
                
                if sense == 'maximize':
                    price = prices.get(item, 0)
                    obj_terms.append(f"{price} * {a_var}")
                
                assign_vars.append((a_var, eff_item_lens[i_idx]))
            
            # Constraint: Capacity with N-1 Correction
            # Sum(Count * (Len + Kerf)) <= (Stock + Kerf) * U_var
            lhs_parts = [f"{length} * {name}" for name, length in assign_vars]
            lhs = " + ".join(lhs_parts)
            
            # Crucial Fix: Use adjusted_stock_len
            constraints.append(f"{lhs} <= {adjusted_stock_len} * {u_var}")

    # 3. Demand Constraints
    for i_idx, item in enumerate(items):
        target = demands.get(item, 0)
        my_a_vars = [v['name'] for v in variables if f"A_IT{i_idx}_" in v['name']]
        
        if not my_a_vars: continue
        lhs = " + ".join(my_a_vars)
        
        if sense == 'minimize':
            constraints.append(f"{lhs} >= {target}")
        else:
            constraints.append(f"{lhs} <= {target}")

    objective_str = " + ".join(obj_terms)
    constraints_str = "\n".join(constraints)
    
    return objective_str, constraints_str, variables
