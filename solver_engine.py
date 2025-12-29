import pulp
import time

def solve_model(store_data, sense, objective_str, constraints_str):
    print("----- [Engine] Start -----")
    try:
        # 1. Setup Context
        variables = store_data.get('variables', [])
        parameters = store_data.get('parameters', [])
        
        lp_sense = pulp.LpMinimize if sense == 'minimize' else pulp.LpMaximize
        prob = pulp.LpProblem("OptiMystic_Problem", lp_sense)
        
        symbol_table = {'pulp': pulp, 'prob': prob}
        
        # 2. Process Parameters
        for p in parameters:
            name = p['name']
            data = p['data']
            shape = p.get('shape', 'scalar')
            if shape in ['list', 'matrix'] or isinstance(data, (list, dict)):
                symbol_table[name] = data
            else:
                try:
                    symbol_table[name] = float(data)
                except:
                    symbol_table[name] = data

        # 3. Process Variables
        for v in variables:
            var_name = v['name']
            var_shape = v.get('shape') # Safely get shape
            var_type = v.get('type', 'Continuous')
            cat = pulp.LpInteger if var_type == 'Integer' else (pulp.LpBinary if var_type == 'Binary' else pulp.LpContinuous)
            
            print(f"[Engine] Creating Var: {var_name}, Shape: {var_shape}")

            if var_shape == 'list':
                indices = range(len(v['data'])) 
                lp_vars = [pulp.LpVariable(f"{var_name}_{i}", lowBound=0, cat=cat) for i in indices]
                symbol_table[var_name] = lp_vars
                
            elif var_shape == 'matrix':
                rows = v['data']
                matrix_vars = {}
                for r_idx, row_data in enumerate(rows):
                    r_lbl = row_data.get('row_label', f"R{r_idx}")
                    matrix_vars[r_lbl] = {}
                    for col_key in row_data.keys():
                        if col_key == 'row_label': continue
                        var_id = f"{var_name}_{r_lbl}_{col_key}"
                        matrix_vars[r_lbl][col_key] = pulp.LpVariable(var_id, lowBound=0, cat=cat)
                symbol_table[var_name] = matrix_vars
            
            else:
                # Fallback for scalar or unknown shape
                symbol_table[var_name] = pulp.LpVariable(var_name, lowBound=0, cat=cat)

        # 4. Objective
        symbol_table['range'] = range
        symbol_table['len'] = len
        
        try:
            # Explicitly pass symbol_table as both globals and locals to ensure visibility
            obj_expr = eval(objective_str, symbol_table, symbol_table)
            prob += obj_expr
        except Exception as e:
            return {'status': 'Error', 'error_msg': f"Objective Error: {e}"}

        # 5. Constraints
        cons_lines = [line.strip() for line in constraints_str.split('\n') if line.strip()]
        for line in cons_lines:
            try:
                con_expr = eval(line, symbol_table, symbol_table)
                prob += con_expr
            except Exception as e:
                return {'status': 'Error', 'error_msg': f"Constraint Error: {e}"}

        # 6. Solve
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=5) 
        prob.solve(solver)
        
        status = pulp.LpStatus[prob.status]
        res_vars = [{'Variable': v.name, 'Value': v.varValue} for v in prob.variables()]
            
        return {
            'status': status,
            'objective': pulp.value(prob.objective),
            'variables': res_vars,
            'constraints': []
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'status': 'Error', 'error_msg': f"System Error:\n{str(e)}"}
