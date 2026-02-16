# modules/cutting/logic_cg.py
import pulp
import time

class CuttingStockCG:
    def __init__(self, params):
        self.items = params.get('Items', [])
        self.demands = params.get('Demands', {})
        self.item_lens = params.get('ItemLens', [])
        self.kerf = float(params.get('Kerf', 0.0))
        
        raw_stocks = params.get('Stocks', [])
        if not raw_stocks:
             self.main_stock = {'Name': 'Default', 'Length': 1000, 'Cost': 100}
        else:
             self.main_stock = max(raw_stocks, key=lambda x: float(x['Length']))
             
        self.stock_len = float(self.main_stock['Length'])
        self.stock_cost = float(self.main_stock['Cost'])

    def solve(self):
        patterns = []
        for i in range(len(self.items)):
            pat = [0] * len(self.items)
            if self.item_lens[i] + self.kerf <= self.stock_len + self.kerf:
                pat[i] = 1
                patterns.append(pat)
        
        loop_count = 0
        while True:
            loop_count += 1
            prob = pulp.LpProblem("Master", pulp.LpMinimize)
            x_vars = [pulp.LpVariable(f"Pat_{j}", lowBound=0) for j in range(len(patterns))]
            prob += pulp.lpSum([x_vars[j] * self.stock_cost for j in range(len(patterns))])
            constraints = []
            for i in range(len(self.items)):
                demand = self.demands[self.items[i]]
                prob += pulp.lpSum([patterns[j][i] * x_vars[j] for j in range(len(patterns))]) >= demand
            prob.solve(pulp.PULP_CBC_CMD(msg=0))
            duals = []
            for name, c in prob.constraints.items():
                duals.append(c.pi)
            if len(duals) != len(self.items):
                duals = [0] * len(self.items)

            kp_prob = pulp.LpProblem("Pricing", pulp.LpMaximize)
            a_vars = [pulp.LpVariable(f"Use_{i}", lowBound=0, cat='Integer') for i in range(len(self.items))]
            kp_prob += pulp.lpSum([duals[i] * a_vars[i] for i in range(len(self.items))])
            kp_lhs = pulp.lpSum([a_vars[i] * (self.item_lens[i] + self.kerf) for i in range(len(self.items))])
            kp_prob += kp_lhs <= (self.stock_len + self.kerf)
            kp_prob.solve(pulp.PULP_CBC_CMD(msg=0))
            best_reduced_val = pulp.value(kp_prob.objective)
            
            if best_reduced_val <= self.stock_cost + 1e-5:
                break
            new_pat = [int(v.varValue) for v in a_vars]
            if new_pat in patterns:
                break
            patterns.append(new_pat)
            if loop_count > 500: 
                break

        final_prob = pulp.LpProblem("Master_Integer", pulp.LpMinimize)
        x_int = [pulp.LpVariable(f"Pattern_{j}", lowBound=0, cat='Integer') for j in range(len(patterns))]
        final_prob += pulp.lpSum([x_int[j] * self.stock_cost for j in range(len(patterns))])
        for i in range(len(self.items)):
            demand = self.demands[self.items[i]]
            final_prob += pulp.lpSum([patterns[j][i] * x_int[j] for j in range(len(patterns))]) >= demand
        final_prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=10))
        
        # Extract dual values from final problem for sensitivity analysis
        final_duals = []
        for name, c in final_prob.constraints.items():
            final_duals.append(c.pi if c.pi else 0.0)
        if len(final_duals) != len(self.items):
            final_duals = [0.0] * len(self.items)
            
        return final_prob, patterns, x_int, final_duals

def format_results_for_dashboard(prob, patterns, x_int, items, duals=None):
    variables = []
    pat_idx = 0
    for j, var in enumerate(x_int):
        count = var.varValue
        if count and count > 0:
            count = int(count)
            pat_content = patterns[j] 
            for k in range(count):
                bin_id = f"CG_Bin_{pat_idx}"
                pat_idx += 1
                variables.append({'Variable': f"U_{bin_id}", 'Value': 1.0})
                for i_idx, qty in enumerate(pat_content):
                    if qty > 0:
                        variables.append({
                            'Variable': f"A_IT{i_idx}_{bin_id}", 
                            'Value': float(qty)
                        })
    
    constraints_data = []
    if duals:
        for i, dual_val in enumerate(duals):
            constraints_data.append({
                'Constraint': f"C_{i}",
                'Shadow Price': dual_val,
                'Slack': 0.0
            })
    
    return {
        'status': pulp.LpStatus[prob.status],
        'objective': pulp.value(prob.objective),
        'variables': variables,
        'constraints': constraints_data
    }