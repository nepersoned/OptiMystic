import pandas as pd

def generate_logic(template_type, params):
    """
    Main entry point for the logic bridge. 
    Routes UI data to specific mathematical generators.
    """
    if template_type == 'transportation':
        return bridge_transportation(params)
    elif template_type == 'prod_mix':
        return bridge_product_mix(params)
    elif template_type == 'blending':
        return bridge_blending(params)
    return "", "", []

# ---------------------------------------------------------
# 1. Transportation Bridge
# ---------------------------------------------------------
def bridge_transportation(params):
    """
    Logic for Logistics/Transportation problems.
    Returns: (Objective, Constraints, Variables_Config)
    """
    plants = params.get('Plants', [])
    regions = params.get('Regions', [])
    
    # Define Matrix Variable for the Solver Engine
    variables = [{
        'name': 'Ship',
        'shape': 'matrix',
        'type': 'Continuous',
        'data': [{'row_label': p, **{r: 0 for r in regions}} for p in plants]
    }]
    
    # Objective: Minimize total shipping cost
    obj_str = "sum(Ship[p][r] * Cost[p][r] for p in Plants for r in Regions)"
    
    # Constraints: Supply limit and Demand satisfaction
    constraints = []
    for p in plants:
        constraints.append(f"sum(Ship['{p}'][r] for r in Regions) <= Supply['{p}']")
    for r in regions:
        constraints.append(f"sum(Ship[p]['{r}'] for p in Plants) >= Demand['{r}']")
        
    return obj_str, "\n".join(constraints), variables

# ---------------------------------------------------------
# 2. Product Mix Bridge
# ---------------------------------------------------------
def bridge_product_mix(params):
    """
    Logic for Production Planning.
    """
    products = params.get('Products', [])
    resources = params.get('Resources', [])
    
    # Define List Variable for the Solver Engine
    variables = [{
        'name': 'Produce',
        'shape': 'list', # Or 'scalar' for each, but list is cleaner
        'type': 'Continuous',
        'data': [{'Product': p} for p in products]
    }]
    
    # Objective: Maximize Profit
    # Since Produce is a list, we access it by index or map it in symbol_table
    obj_str = "sum(Produce[i] * Profit[products[i]] for i in range(len(products)))"
    
    constraints = []
    for res in resources:
        constraints.append(f"sum(Produce[i] * Usage['{res}'][products[i]] for i in range(len(products))) <= Capacity['{res}']")
        
    return obj_str, "\n".join(constraints), variables

# ---------------------------------------------------------
# 3. Blending Bridge
# ---------------------------------------------------------
def bridge_blending(params):
    """
    Logic for Ingredient Mixture optimization.
    """
    ingr = params.get('Ingredients', [])
    
    variables = [{
        'name': 'W', # Weight of each ingredient
        'shape': 'list',
        'type': 'Continuous',
        'data': [{'Ingr': i} for i in ingr]
    }]
    
    # Objective: Minimize Cost
    obj_str = "sum(W[i] * Cost[ingr[i]] for i in range(len(ingr)))"
    
    # Constraints: Nutritional requirements
    min_a = params.get('min_a', 0)
    min_b = params.get('min_b', 0)
    
    constraints = [
        f"sum(W[i] * NutA[ingr[i]] for i in range(len(ingr))) >= {min_a}",
        f"sum(W[i] * NutB[ingr[i]] for i in range(len(ingr))) >= {min_b}"
    ]
    
    return obj_str, "\n".join(constraints), variables
