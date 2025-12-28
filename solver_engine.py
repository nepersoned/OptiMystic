import pulp

def solve_model(store_data, sense, objective_str, constraints_str):
    """
    [V2 Upgrade] Version supporting list/matrix variables and sum() function.
    """
    # 1. Initialize Model
    sense_obj = pulp.LpMinimize if sense == 'minimize' else pulp.LpMaximize
    prob = pulp.LpProblem("OptiMystic_Model", sense_obj)
    
    # 2. Symbol Table (Storage for variables/parameters)
    # Register pulp.lpSum as 'sum' -> Allows user to use sum(...) in formulas
    symbol_table = {'sum': pulp.lpSum}
    
    # --- [Step 1] Load Parameters (Constants) ---
    for p in store_data.get('parameters', []):
        name = p['name']
        shape = p['shape']
        data = p['data']
        
        if shape == 'scalar':
            symbol_table[name] = float(data)
        elif shape == 'matrix':
            # Matrix: Nested dictionary in {Row: {Col: Val}} format
            mat_dict = {}
            for row in data:
                r_label = row.get('row_label', 'Row')
                mat_dict[r_label] = {k: v for k, v in row.items() if k != 'row_label'}
            symbol_table[name] = mat_dict
        elif shape == 'list':
            # List: Stored as Raw List of Dicts
            symbol_table[name] = data

    # --- [Step 2] Create Decision Variables ---
    for v in store_data.get('variables', []):
        name = v['name']
        shape = v['shape']
        v_type = v['type']
        
        cat = pulp.LpContinuous
        if v_type == 'Integer': cat = pulp.LpInteger
        elif v_type == 'Binary': cat = pulp.LpBinary
        
        if shape == 'scalar':
            new_var = pulp.LpVariable(name, lowBound=0, cat=cat)
            symbol_table[name] = new_var
            
        elif shape == 'matrix':
            # Matrix variables need to borrow keys from parameters to be created correctly.
            # Since the current Wizard does not specify a 'reference set', 
            # we temporarily create it as a scalar to prevent errors.
            # (To be upgraded in V3 for full matrix support)
            symbol_table[name] = pulp.LpVariable(name, lowBound=0, cat=cat)

        elif shape == 'list':
            # List variables: Preparation for multi-dimensional variables (LpVariable.dicts)
            # Currently treated as a single variable for safety.
            symbol_table[name] = pulp.LpVariable(name, lowBound=0, cat=cat)

    # --- [Step 3] Parse Objective Function ---
    try:
        if objective_str:
            # Safe eval execution
            obj_expr = eval(objective_str, {"__builtins__": None}, symbol_table)
            prob += obj_expr, "Objective"
    except Exception as e:
        return f"Error in Objective: {str(e)}"

    # --- [Step 4] Parse Constraints ---
    if constraints_str:
        lines = constraints_str.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            try:
                constr_expr = eval(line, {"__builtins__": None}, symbol_table)
                prob += constr_expr, f"Constraint_{i+1}"
            except Exception as e:
                return f"Error in Constraint line {i+1} ('{line}'):\n{str(e)}"

    # --- [Step 5] Run Solver ---
    try:
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
    except Exception as e:
        return f"Solver Execution Error: {str(e)}"

    # --- [Step 6] Format Results (Text) ---
    status = pulp.LpStatus[prob.status]
    result_txt = [f"Solver Status: {status}"]
    
    if prob.status == pulp.LpStatusOptimal:
        val = pulp.value(prob.objective)
        result_txt.append(f"Objective Value: {val:,.2f}") # Add thousand separators
        result_txt.append("-" * 30)
        result_txt.append("[Variables]")
        
        # Sort variables by name and output
        for v in sorted(prob.variables(), key=lambda x: x.name):
            if v.varValue is not None and abs(v.varValue) > 1e-5: # Output only non-zero values
                result_txt.append(f"  {v.name} = {v.varValue}")
    else:
        result_txt.append("No optimal solution found.")
        
    return "\n".join(result_txt)
