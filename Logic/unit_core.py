class UnitVariable:
  def __init__(self,value,unit_num,unit_denom="1",var_type):
    self.value = float(value)
    self.unit_num = unit_num
    self.unit_denom = unit_denom
    self.var_type = var_type


  def __repr__(self):
    if self.unit_denom == "1":
      base_str = f"{self.value} [{self.unit_num}]"

    else:
      base_str = f"{self.value} [{self.unit_num}/{self.unit_denom}]"
      
    return f"{base_str} ({self.var_type})"
      
def parse_table_to_objects(rows):
    variables = {} 

    for row in rows:
        var_name = row.get('var_name')
        
        if not var_name or var_name.strip() == '': 
            continue
        
        try:
    
            val = float(row.get('value', 0))
            
            u_num = row.get('unit_num', '1')
            u_denom = row.get('unit_denom', '1')
            v_type = row.get('var_type', 'Continuous')
          
            new_var = UnitVariable(val, u_num, u_denom, v_type)
            variables[var_name] = new_var
            
        except ValueError:
            print(f"[Parser Warning] 변수 '{var_name}'의 값이 숫자가 아니어서 무시됩니다.")
            continue

    return variables

