import pulp

def solve_model(store_data, sense, objective_str, constraints_str):
    sense_obj = pulp.LpMinimize if sense == 'minimize' else pulp.LpMaximize
    prob = pulp.LpProblem("OptiMystic_Model", sense_obj)
    
    symbol_table = {}
    
    # Parameters
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

    # Variables
    for v in store_data.get('variables', []):
        name = v['name']
        shape = v['shape']
        v_type = v['type']
        
        cat = pulp.LpContinuous
        if v_type == 'Integer': cat = pulp.LpInteger
        elif v_type == 'Binary': cat = pulp.LpBinary
        
        new_var = pulp.LpVariable(name, lowBound=0, cat=cat)
        symbol_table[name] = new_var

    # Objective
    try:
        if objective_str:
            obj_expr = eval(objective_str, {"__builtins__": None}, symbol_table)
            prob += obj_expr, "Objective"
    except Exception as e:
        return f"Error in Objective: {str(e)}"

    # Constraints
    if constraints_str:
        lines = constraints_str.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            try:
                constr_expr = eval(line, {"__builtins__": None}, symbol_table)
                prob += constr_expr, f"Constraint_{i+1}"
            except Exception as e:
                return f"Error in Constraint line {i+1} ('{line}'): {str(e)}"

    # Solve
    try:
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
    except Exception as e:
        return f"Solver Execution Error: {str(e)}"

    # Results
    status = pulp.LpStatus[prob.status]
    result_txt = [f"Solver Status: {status}"]
    
    if prob.status == pulp.LpStatusOptimal:
        result_txt.append(f"Objective Value: {pulp.value(prob.objective)}")
        result_txt.append("\n[Variables]")
        for v in prob.variables():
            result_txt.append(f"  {v.name} = {v.varValue}")
    else:
        result_txt.append("No optimal solution found.")
        
    return "\n".join(result_txt)
