# bridge_logic.py
import logic_cutting as cut_logic
import logic_cg as cut_logic_cg

def generate_logic(template_type, params):
    if template_type == 'cutting':
        sense = params.get('Sense', 'minimize')
        
        if sense == 'minimize':
            # Execute Column Generation
            cg_solver = cut_logic_cg.CuttingStockCG(params)
            prob, patterns, x_int, duals = cg_solver.solve()
            
            # Format results for the dashboard
            res_dict = cut_logic_cg.format_results_for_dashboard(prob, patterns, x_int, params['Items'], duals)
            
            fixed_vars = []
            constraints = []
            obj_parts = []

            # Build structured objective terms and fixed constraints
            for v in res_dict['variables']:
                fixed_vars.append({'name': v['Variable'], 'type': 'Continuous'})
                if v['Variable'].startswith('U_'):
                    obj_parts.append({'coef': float(cg_solver.stock_cost), 'var': v['Variable']})
                # Lock values to optimized state
                constraints.append({'type': 'fix', 'var': v['Variable'], 'value': float(v['Value'])})

            # Demand constraints (structured)
            demand_consts = []
            for i, name in enumerate(params['Items']):
                item_var_names = [v['Variable'] for v in res_dict['variables'] if v['Variable'].startswith(f"A_IT{i}_")]
                if item_var_names:
                    terms = [{'coef': 1.0, 'var': vn} for vn in item_var_names]
                    demand_consts.append({'type': 'linear', 'terms': terms, 'sense': '>=', 'rhs': float(params['Demands'][name])})

            objective_terms = obj_parts if obj_parts else []
            return objective_terms, demand_consts + constraints, fixed_vars
        
        else:
            # Profit maximization mode (MIP)
            return cut_logic.bridge_cutting(params)
            
    return "", "", []