import pulp

def solve_model(store_data, sense, objective_str, constraints_str):
    """
    [V3 Upgrade] Supports proper Matrix/List Variable instantiation.
    Now 'x' can be accessed as x['Row']['Col'] or x[0] in formulas.
    """
    # 1. Initialize Model
    sense_obj = pulp.LpMinimize if sense == 'minimize' else pulp.LpMaximize
    prob = pulp.LpProblem("OptiMystic_Model", sense_obj)
    
    # 2. Symbol Table & Helper Lists
    # rows/cols helper: to iterate in formula like [x[r][c] for r in rows...]
    symbol_table = {'sum': pulp.lpSum}
    
    # --- [Step 1] Load Parameters (Constants) ---
    for p in store_data.get('parameters', []):
        name = p['name']
        shape = p['shape']
        data = p['data']
        
        if shape == 'scalar':
            symbol_table[name] = float(data)
        elif shape == 'matrix':
            # Matrix: {Row: {Col: Val}}
            mat_dict = {}
            rows = []
            cols = []
            for row in data:
                r_label = row.get('row_label', 'Row')
                rows.append(r_label)
                row_data = {k: v for k, v in row.items() if k != 'row_label'}
                mat_dict[r_label] = row_data
                if not cols: cols = list(row_data.keys())
            
            symbol_table[name] = mat_dict
            # Add helper lists for iteration (e.g., Cost_rows, Cost_cols)
            symbol_table[f"{name}_rows"] = rows
            symbol_table[f"{name}_cols"] = cols
            
        elif shape == 'list':
            symbol_table[name] = data

    # --- [Step 2] Create Decision Variables ---
    for v in store_data.get('variables', []):
        name = v['name']
        shape = v['shape']
        v_type = v['type']
        real_data = v.get('data') # This contains the grid structure from UI
        
        cat = pulp.LpContinuous
        if v_type == 'Integer': cat = pulp.LpInteger
        elif v_type == 'Binary': cat = pulp.LpBinary
        
        if shape == 'scalar':
            new_var = pulp.LpVariable(name, lowBound=0, cat=cat)
            symbol_table[name] = new_var
            
        elif shape == 'matrix':
            # Create a Dictionary of Variables: Var['Row']['Col']
            if not real_data: # Fallback if empty
                symbol_table[name] = pulp.LpVariable(name, lowBound=0, cat=cat)
                continue
                
            var_dict = {}
            rows = []
            cols = []
            
            for row in real_data:
                r_label = row.get('row_label', 'Row')
                rows.append(r_label)
                var_dict[r_label] = {}
                
                # Get columns (excluding row_label)
                current_cols = [k for k in row.keys() if k != 'row_label']
                if not cols: cols = current_cols
                
                for c in current_cols:
                    # Var Name: Flow_Factory1_WarehouseA
                    var_name = f"{name}_{r_label}_{c}"
                    new_var = pulp.LpVariable(var_name, lowBound=0, cat=cat)
                    var_dict[r_label][c] = new_var
            
            symbol_table[name] = var_dict
            # Helper sets for iteration
            symbol_table[f"{name}_rows"] = rows
            symbol_table[f"{name}_cols"] = cols

        elif shape == 'list':
            # Create a List of Variables: Var[0], Var[1]...
            if not real_data:
                symbol_table[name] = pulp.LpVariable(name, lowBound=0, cat=cat)
                continue
                
            var_list = []
            for i, item in enumerate(real_data):
                var_name = f"{name}_{i}"
                new_var = pulp.LpVariable(var_name, lowBound=0, cat=cat)
                var_list.append(new_var)
            
            symbol_table[name] = var_list

    # --- [Step 3 & 4] Parse Objective & Constraints ---
    # Helper context for eval
    eval_context = {"__builtins__": None}
    
    try:
        if objective_str:
            obj_expr = eval(objective_str, eval_context, symbol_table)
            prob += obj_expr, "Objective"
            
        if constraints_str:
            lines = constraints_str.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if not line: continue
                try:
                    constr_expr = eval(line, eval_context, symbol_table)
                    prob += constr_expr, f"Constraint_{i+1}"
                except Exception as e:
                    return f"❌ Error in Constraint {i+1}:\n{str(e)}"
                    
        # --- [Step 5] Run Solver ---
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
    except Exception as e:
        return f"❌ Model Error: {str(e)}"

    # --- [Step 6] Format Results ---
    status = pulp.LpStatus[prob.status]
    result_txt = [f"Solver Status: {status}"]
    
    if prob.status == pulp.LpStatusOptimal:
        val = pulp.value(prob.objective)
        result_txt.append(f"Objective Value: {val:,.2f}")
        result_txt.append("-" * 30)
        result_txt.append("[Variables]")
        
        # Smart Printing: Flatten dictionaries for display
        sorted_vars = sorted(prob.variables(), key=lambda x: x.name)
        for v in sorted_vars:
            if v.varValue is not None and abs(v.varValue) > 1e-5:
                result_txt.append(f"  {v.name} = {v.varValue}")
    else:
        result_txt.append("No optimal solution found.")
        
    return "\n".join(result_txt)
