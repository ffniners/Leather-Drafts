import ast, operator as op
from typing import Any, Dict

ALLOWED = {
    "abs": abs, "min": min, "max": max, "round": round
}
OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Pow: op.pow, ast.USub: op.neg
}

def _eval(node, env):
    if isinstance(node, ast.Num):     # 3.8: ast.Num; 3.11: ast.Constant
        return node.n
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return OPS[type(node.op)](_eval(node.left, env), _eval(node.right, env))
    if isinstance(node, ast.UnaryOp):
        return OPS[type(node.op)](_eval(node.operand, env))
    if isinstance(node, ast.Name):
        if node.id in env: return env[node.id]
        if node.id in ALLOWED: return ALLOWED[node.id]
        raise ValueError(f"name not allowed: {node.id}")
    if isinstance(node, ast.Call):
        func = _eval(node.func, env)
        args = [_eval(a, env) for a in node.args]
        return func(*args)
    if isinstance(node, ast.Attribute):
        # allow M.chest, F.ease_chest, O.hem_allowance
        base = _eval(node.value, env)
        return base[node.attr]
    raise ValueError("bad expression")

def eval_expr(expr: str, env: Dict[str, Any]) -> float:
    tree = ast.parse(expr, mode="eval").body
    return float(_eval(tree, env))
