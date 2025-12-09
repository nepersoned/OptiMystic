class UnitVariable:
  def __init__(self,value,unit_num,unit_denom="1"):
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
      
  

