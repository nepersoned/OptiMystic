import re

class UnitVariable:
    def __init__(self, value, unit_num, unit_denom="1", var_type="Continuous", indices=None, index_range=None):
        try:
            if value is None or str(value).strip() == '':
                self.value = 0.0
            else:
                self.value = float(value)
        except ValueError:
            self.value = 0.0 # 안전 장치
            
        self.unit_num = unit_num
        self.unit_denom = unit_denom
        self.var_type = var_type
        self.indices = indices if indices else []  
        self.index_range = index_range             

    def __repr__(self):
        if self.unit_denom == "1":
            unit_str = f"[{self.unit_num}]"
        else:
            unit_str = f"[{self.unit_num}/{self.unit_denom}]"

        idx_str = ""
        if self.indices:
            idx_str = f"_{{{','.join(self.indices)}}}"
            
        return f"{self.value}{unit_str} ({self.var_type}{idx_str})"

def parse_variable_name(name_str):
    예: "Cost[i,j]" -> name="Cost", indices=["i", "j"]
    예: "Budget"    -> name="Budget", indices=[]
    """
    if not name_str:
        return "N/A", []

    pattern = r'([A-Za-z0-9_]+)\[(.*?)\]'
    match = re.fullmatch(pattern, name_str.strip())
    
    if match:
        name = match.group(1)
        indices_str = match.group(2)
        indices = [i.strip() for i in indices_str.split(',') if i.strip()]
    else:
        name = name_str.strip()
        indices = []
    
    return name, indices
      
def parse_table_to_objects(rows):
    """
    Dash DataTable의 rows 데이터를 받아 UnitVariable 객체들을 담은 딕셔너리로 변환합니다.
    
    Returns:
        variables (dict): { "변수명": UnitVariable객체, ... }
        error_report (list): 파싱 중 발생한 치명적인 에러 메시지 리스트
    """
    variables = {}
    error_report = [] 
    
    if not rows:
        return variables, error_report

    for i, row in enumerate(rows): 
        raw_name = row.get('var_name', 'N/A')
        name, parsed_indices = parse_variable_name(raw_name)
        
        try:
            val_input = row.get('value')
            if val_input is None or str(val_input).strip() == '':
                val = 0.0
            else:
                val = float(val_input)
            u_num = row.get('unit_num', '1')
            u_denom = row.get('unit_denom', '1')
            v_type = row.get('var_type', 'Continuous')
            idx_range = row.get('index_range', '')
            new_var = UnitVariable(
                value=val, 
                unit_num=u_num, 
                unit_denom=u_denom, 
                var_type=v_type, 
                indices=parsed_indices, 
                index_range=idx_range 
            )
            
            variables[name] = new_var
            
        except ValueError:
            error_report.append(f"❌ {i+1}행 ('{raw_name}') 처리 중 내부 오류 발생")
            continue

    return variables, error_report
