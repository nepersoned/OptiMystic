import pulp

def solve_model(store_data, sense, objective_str, constraints_str):
    """
    [V4 Upgrade] Returns structured dictionary data (JSON-ready) instead of plain text.
    Target: Visualization Dashboard (Phase 5)
    """
    # 1. Initialize Model
    sense_obj = pulp.LpMinimize if sense == 'minimize' else pulp.LpMaximize
    prob = pulp.LpProblem("OptiMystic_Model", sense_obj)
    
    # 2. Symbol Table & Helpers
    symbol_table = {'sum': pulp.lpSum}
    
    # --- [Step 1] Parameters ---
    for p in store_data.get('parameters', []):
        name = p['name']
        shape = p['shape']
        data = p['data']
        
        if shape == 'scalar':
            symbol_table[name] = float(data)
        elif shape == 'matrix':
            mat_dict = {}
            for row in data:
                r_label = row.get('row_label', 'Row')
                mat_dict[r_label] = {k: v for k, v in row.items() if k != 'row_label'}
            symbol_table[name] = mat_dict
        elif shape == 'list':
            symbol_table[name] = data

    # --- [Step 2] Variables ---
    for v in store_data.get('variables', []):
        name = v['name']
        shape = v['shape']
        v_type = v['type']
        real_data = v.get('data')
        
        cat = pulp.LpContinuous
        if v_type == 'Integer': cat = pulp.LpInteger
        elif v_type == 'Binary': cat = pulp.LpBinary
        
        if shape == 'scalar':
            symbol_table[name] = pulp.LpVariable(name, lowBound=0, cat=cat)
            
        elif shape == 'matrix':
            # Handle Matrix variables (Create dict of variables)
            if not real_data:
                symbol_table[name] = pulp.LpVariable(name, lowBound=0, cat=cat)
                continue
            var_dict = {}
            for row in real_data:
                r_label = row.get('row_label', 'Row')
                var_dict[r_label] = {}
                # Extract columns excluding the label
                for c in [k for k in row.keys() if k != 'row_label']:
                    var_name = f"{name}_{r_label}_{c}"
                    var_dict[r_label][c] = pulp.LpVariable(var_name, lowBound=0, cat=cat)
            symbol_table[name] = var_dict

        elif shape == 'list':
            # Handle List variables (Create list of variables)
            if not real_data:
                symbol_table[name] = pulp.LpVariable(name, lowBound=0, cat=cat)
                continue
            var_list = []
            for i, item in enumerate(real_data):
                var_list.append(pulp.LpVariable(f"{name}_{i}", lowBound=0, cat=cat))
            symbol_table[name] = var_list

    # --- [Step 3 & 4] Parse & Solve ---
    try:
        # Parse Objective
        if objective_str:
            prob += eval(objective_str, {"__builtins__": None}, symbol_table), "Objective"
        
        # Parse Constraints
        if constraints_str:
            for i, line in enumerate(constraints_str.split('\n')):
                if line.strip():
                    prob += eval(line, {"__builtins__": None}, symbol_table), f"Constraint_{i+1}"
        
        # Run Solver
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
    except Exception as e:
        return {'status': 'Error', 'error_msg': str(e)}

    # --- [Step 5] Build Result Dictionary ---
    status = pulp.LpStatus[prob.status]
    results = {
        'status': status,
        'objective': 0,
        'variables': [],
        'error_msg': None
    }
    
    if prob.status == pulp.LpStatusOptimal:
        results['objective'] = pulp.value(prob.objective)
        # Collect non-zero variables
        for v in prob.variables():
            if v.varValue is not None and abs(v.varValue) > 1e-5:
                # Format name: Flow_Busan_Shop2 -> Flow [Busan, Shop2]
                clean_name = v.name.replace('_', ' ')
                results['variables'].append({'Variable': clean_name, 'Value': v.varValue})
    
    return results
