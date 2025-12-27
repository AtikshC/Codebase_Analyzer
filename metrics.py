import ast

def analyze_file(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()

    tree = ast.parse(source)

    lines = source.splitlines()
    total_lines = len(lines)

    todos = sum(
        1 for line in lines
        if "TODO" in line or "FIXME" in line
    )

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start = node.lineno
            end = max(
                [n.lineno for n in ast.walk(node) if hasattr(n, "lineno")],
                default=start
            )
            functions.append(end - start + 1)

    return {
        "lines": total_lines,
        "functions": len(functions),
        "function_lengths": functions,
        "todos": todos
    }
