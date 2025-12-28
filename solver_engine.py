import pulp

def build_pulp_variables(store_data):
    pulp_vars = {}
    params = {}
    
    for p in store_data.get('parameters', []):
        name = p['name']
        shape = p['shape']
        data = p['data']
        
        if shape == 'scalar':
            params[name] = float(data)
        elif shape == 'matrix':
            # data는 [{'row_label': 'Factory_A', 'Warehouse_1': 10, ...}, ...] 형태임
            mat_dict = {}
            for row in data:
                r_label = row['row_label']
                mat_dict[r_label] = {k: v for k, v in row.items() if k != 'row_label'}
            params[name] = mat_dict
        elif shape == 'list':
            params[name] = data

    for v in store_data.get('variables', []):
        name = v['name']
        shape = v['shape']
        v_type = v['type'] # Continuous, Integer, Binary

        cat = pulp.LpContinuous
        if v_type == 'Integer': cat = pulp.LpInteger
        elif v_type == 'Binary': cat = pulp.LpBinary

        if shape == 'scalar':
            pulp_vars[name] = pulp.LpVariable(name, lowBound=0, cat=cat)

        elif shape == 'matrix':
            pass 

        elif shape == 'list':
            pass

    return pulp_vars, params
