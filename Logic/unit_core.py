class UnitVariable:
  def __inint__(self,value,unit,num,unit_denom="1")
  self.value = float(value)
  self.unit_num = unit_num
  self.unit_denom = unit_denom


  def __reper(self):
    if self.unit_denom = 1:
      return f"{self.value} [{self.unit_num}]"

    else:
      return f"{self.value} [{self.unit_num}/{self.unit_denom}]"
      
  
#TEST CODE
if __name__ == "__main__":
    print("🔮 OptiMystic Unit Core Test...")
    v1 = UnitVariable(80, "시간") 
    v2 = UnitVariable(1000, "원", "시간")
    
    print(f"결과 1: {v1}") # 목표: 80.0 [시간]
    print(f"결과 2: {v2}") # 목표: 1000.0 [원/시간]
