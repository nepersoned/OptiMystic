# solver_engine.py
import pulp
import time

def solve_model(store_data, sense, objective, constraints):
    start_time = time.time()
    
    # Setup Optimization Sense
    lp_sense = pulp.LpMinimize if sense == 'minimize' else pulp.LpMaximize
    prob = pulp.LpProblem("OptiMystic_Solver", lp_sense)
    
    # Build pulp variables map
    safe_symbols = {}
    parameters = {p['name']: p['data'] for p in store_data.get('parameters', [])}
    for v in store_data.get('variables', []):
        cat = pulp.LpInteger if v.get('type') == 'Integer' else (pulp.LpBinary if v.get('type') == 'Binary' else pulp.LpContinuous)
        safe_symbols[v['name']] = pulp.LpVariable(v['name'], lowBound=0, cat=cat)

    try:
        # Build objective
        if isinstance(objective, list):
            prob += pulp.lpSum([term.get('coef', 0) * safe_symbols[term['var']] for term in objective])
        elif isinstance(objective, str) and objective.strip():
            # fallback to legacy string eval (kept for backward compatibility)
            prob += eval(objective, {'__builtins__': None}, safe_symbols)
        else:
            prob += 0

        # Parse structured constraints
        if isinstance(constraints, list):
            for idx, c in enumerate(constraints):
                ctype = c.get('type', 'linear')
                if ctype == 'fix':
                    var = c['var']; val = c['value']
                    prob += (safe_symbols[var] == val, f"C_fix_{idx}")
                elif ctype == 'linear':
                    terms = c.get('terms', [])
                    lhs = pulp.lpSum([t.get('coef', 0) * safe_symbols[t['var']] for t in terms])
                    sense = c.get('sense', '<=')
                    rhs = c.get('rhs', 0)
                    if sense == '<=':
                        prob += (lhs <= rhs, f"C_{idx}")
                    elif sense == '>=':
                        prob += (lhs >= rhs, f"C_{idx}")
                    else:
                        prob += (lhs == rhs, f"C_{idx}")
                else:
                    # unknown constraint type; skip
                    continue
        elif isinstance(constraints, str) and constraints.strip():
            lines = [l.strip() for l in str(constraints).split('\n') if l.strip()]
            for idx, line in enumerate(lines):
                prob += (eval(line, {'__builtins__': None}, safe_symbols), f"C_{idx}")

        # Execute Solver
        prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=10))
        
        # Extract dual values from constraints
        constraints_data = []
        for name, c in prob.constraints.items():
            constraints_data.append({
                'Constraint': name,
                'Shadow Price': c.pi if c.pi is not None else 0.0,
                'Slack': c.slack if c.slack is not None else 0.0
            })
        
        # Package Results
        res_vars = [{'Variable': v.name, 'Value': v.varValue} for v in prob.variables()]
        
        return {
            'status': pulp.LpStatus[prob.status],
            'objective': pulp.value(prob.objective),
            'variables': res_vars,
            'constraints': constraints_data,
            'solve_time': time.time() - start_time
        }
    except Exception as e:
        return {'status': 'Error', 'error_msg': str(e)}
