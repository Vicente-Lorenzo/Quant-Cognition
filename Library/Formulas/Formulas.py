import xlwings as xw
from functools import wraps

def formula(func):
    @xw.func
    @wraps(func)
    def wrapper(*args):
        try:
            result = func(*args)
            if result is None or (hasattr(result, "__len__") and len(result) == 0):
                return "Error: No Data"
            return result
        except Exception as e:
            return f"Error: {e}"
    return wrapper