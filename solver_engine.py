import pulp
import time

def solve_model(store_data, sense, objective_str, constraints_str):
    print("----- [Engine] Start -----")
    
    # 1. Setup Context
    variables = store_data.get('variables', [])
    parameters = store_data.get('parameters', [])
    
    # Define LP Problem
    lp_sense = pulp.LpMinimize if sense == 'minimize' else pulp.LpMaximize
    prob = pulp.LpProblem("OptiMystic_Problem", lp_sense)
    
    symbol_table = {'pulp': pulp, 'prob': prob}
    
    try:
        # 2. Process Parameters
        for p in parameters:
            name = p['name']
            data = p['data']
            symbol_table[name] = data

        # 3. Process Variables
        for v in variables:
            var_name = v['name']
            var_type = v.get('type', 'Continuous')
            cat = pulp.LpInteger if var_type == 'Integer' else (pulp.LpBinary if var_type == 'Binary' else pulp.LpContinuous)
            
            # Shape Handling
            shape = v.get('shape', 'scalar')
            if shape == 'list':
                indices = range(len(v['data']))
                symbol_table[var_name] = [pulp.LpVariable(f"{var_name}_{i}", lowBound=0, cat=cat) for i in indices]
            elif shape == 'matrix':
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
                symbol_table[var_name] = pulp.LpVariable(var_name, lowBound=0, cat=cat)

        # 4. Objective
        symbol_table['range'] = range
        symbol_table['len'] = len
        try:
            obj_expr = eval(objective_str, symbol_table, symbol_table)
            prob += obj_expr
        except Exception as e:
            return {'status': 'Error', 'error_msg': f"Objective Logic Error: {e}"}

        # 5. Constraints
        cons_lines = [line.strip() for line in constraints_str.split('\n') if line.strip()]
        for idx, line in enumerate(cons_lines):
            try:
                con_expr = eval(line, symbol_table, symbol_table)
                prob += (con_expr, f"C_{idx}")
            except Exception as e:
                return {'status': 'Error', 'error_msg': f"Constraint Error (Line {idx+1}): {e}"}

        # 6. Solve
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=60)
        prob.solve(solver)
        
        status = pulp.LpStatus[prob.status]
        
        # --- [PATCH] Smart Infeasible Diagnosis ---
        if status == 'Infeasible':
            print("[Engine] ⚠️ Infeasible detected. Starting Analysis...")
            
            # Calculate Total Supply vs Total Demand (Heuristic)
            total_supply = 0
            total_demand = 0
            
            # Extract Data safely
            stocks = symbol_table.get('Stocks', [])
            items = symbol_table.get('Items', [])
            demands = symbol_table.get('Demands', {})
            item_lens = symbol_table.get('ItemLens', [])
            
            if stocks and items:
                # 1. Check Capacity
                for s in stocks:
                    total_supply += (float(s['Length']) * float(s['Limit']))
                
                for i, l in zip(items, item_lens):
                    qty = demands.get(i, 0)
                    total_demand += (float(l) * float(qty))
                    
                gap = total_demand - total_supply
                
                diagnosis_msg = "### ⚠️ Optimization Failed (Infeasible)\n"
                diagnosis_msg += "The solver cannot find a solution. Here is the AI diagnosis:\n\n"
                
                if gap > 0:
                    diagnosis_msg += f"**1. Critical Material Shortage:**\n"
                    diagnosis_msg += f"- You need at least **{gap:,.0f} mm** more material.\n"
                    diagnosis_msg += f"- Total Demand: {total_demand:,.0f} mm\n"
                    diagnosis_msg += f"- Max Supply: {total_supply:,.0f} mm\n\n"
                else:
                    diagnosis_msg += "**1. Stock Length Issue:**\n"
                    diagnosis_msg += "- You have enough total length, but individual items might be longer than your longest stock bar.\n\n"
                
                diagnosis_msg += "**👉 Suggested Actions:**\n"
                diagnosis_msg += "- Increase the 'Limit' (quantity) of your stocks.\n"
                diagnosis_msg += "- Add a new longer stock type."
                
                return {
                    'status': 'Infeasible',
                    'objective': 0,
                    'variables': [],
                    'constraints': [],
                    'error_msg': diagnosis_msg
                }
            else:
                # Fallback for non-cutting problems
                return {
                    'status': 'Infeasible',
                    'objective': 0,
                    'variables': [],
                    'constraints': [],
                    'error_msg': "### ⚠️ Infeasible Problem\nThe constraints are too tight. Please check your logic."
                }

        # Standard Success Result
        res_vars = [{'Variable': v.name, 'Value': v.varValue} for v in prob.variables()]
        constraints_data = []
        for name, c in prob.constraints.items():
            try:
                constraints_data.append({'Constraint': name, 'Shadow Price': c.pi, 'Slack': c.slack})
            except:
                pass 

        return {
            'status': status,
            'objective': pulp.value(prob.objective),
            'variables': res_vars,
            'constraints': constraints_data
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'status': 'Error', 'error_msg': f"System Error:\n{str(e)}"}
