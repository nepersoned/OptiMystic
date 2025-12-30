# Import the separated logic module
import modules.cutting.logic as cut_logic 

def generate_logic(template_type, params):
    if template_type == 'cutting': 
        # Redirect to the new modular logic
        return cut_logic.bridge_cutting(params)
        
    elif template_type == 'transportation': return bridge_transportation(params)
    elif template_type == 'prod_mix': return bridge_product_mix(params)
    elif template_type == 'blending': return bridge_blending(params)
    return "", "", []

# ---------------------------------------------------------
# Other Bridges (Kept strictly for legacy support)
# ---------------------------------------------------------
def bridge_transportation(params):
    plants = params.get('Plants', [])
    regions = params.get('Regions', [])
    variables = [{'name': 'Ship', 'shape': 'matrix', 'type': 'Continuous', 'data': [{'row_label': p, **{r: 0 for r in regions}} for p in plants]}]
    obj_str = "sum(Ship[p][r] * Cost[p][r] for p in Plants for r in Regions)"
    constraints = []
    for p in plants: constraints.append(f"sum(Ship['{p}'][r] for r in Regions) <= Supply['{p}']")
    for r in regions: constraints.append(f"sum(Ship[p]['{r}'] for p in Plants) >= Demand['{r}']")
    return obj_str, "\n".join(constraints), variables

def bridge_product_mix(params):
    products = params.get('Products', [])
    resources = params.get('Resources', [])
    variables = [{'name': 'Produce', 'shape': 'list', 'type': 'Continuous', 'data': [{'Product': p} for p in products]}]
    obj_str = "sum(Produce[i] * Profit[products[i]] for i in range(len(products)))"
    constraints = []
    for res in resources: constraints.append(f"sum(Produce[i] * Usage['{res}'][products[i]] for i in range(len(products))) <= Capacity['{res}']")
    return obj_str, "\n".join(constraints), variables

def bridge_blending(params):
    ingr = params.get('Ingredients', [])
    variables = [{'name': 'W', 'shape': 'list', 'type': 'Continuous', 'data': [{'Ingr': i} for i in ingr]}]
    obj_str = "sum(W[i] * Cost[ingr[i]] for i in range(len(ingr)))"
    min_a = params.get('min_a', 0)
    min_b = params.get('min_b', 0)
    constraints = [f"sum(W[i] * NutA[ingr[i]] for i in range(len(ingr))) >= {min_a}", f"sum(W[i] * NutB[ingr[i]] for i in range(len(ingr))) >= {min_b}"]
    return obj_str, "\n".join(constraints), variables
