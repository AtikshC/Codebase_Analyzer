# analyze.py
import os
import ast
import sys

from database import init_db, store_scan
from report import generate_report
from health import analyze_health


def _is_python_file(name: str) -> bool:
    return name.endswith(".py") and not name.startswith(".")


def _safe_read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _max_nesting_depth(node: ast.AST) -> int:
    """
    Measures structural nesting depth of a function body.
    We count only common block nodes that add nesting.
    """
    nesting_nodes = (
        ast.If,
        ast.For,
        ast.While,
        ast.With,
        ast.Try,
        ast.Match,  # py3.10+
    )

    def dfs(n: ast.AST, depth: int) -> int:
        best = depth
        for child in ast.iter_child_nodes(n):
            if isinstance(child, nesting_nodes):
                best = max(best, dfs(child, depth + 1))
            else:
                best = max(best, dfs(child, depth))
        return best

    return dfs(node, 0)


def analyze(project_path: str) -> None:
    # ----------------------------
    # METRICS THAT FEED SCORING
    # ----------------------------
    metrics = {
        # size / scale
        "files_scanned": 0,
        "total_lines": 0,
        "total_functions": 0,

        # readability
        "long_functions": 0,
        "many_param_functions": 0,
        "deeply_nested_functions": 0,

        # maintainability
        "large_files": 0,
        "too_many_functions_files": 0,
        "high_todo_density": 0,
        "duplicate_function_names": 0,

        # complexity
        "high_branch_functions": 0,
        "many_loop_functions": 0,
        "god_functions": 0,

        # safety/style
        "empty_except_blocks": 0,
        "wildcard_imports": 0,
        "print_count": 0,
    }

    # ----------------------------
    # THRESHOLDS (easy to tune)
    # ----------------------------
    MAX_FILE_LINES = 400
    MAX_FUNCTION_LENGTH = 50
    MAX_PARAMS = 5
    MAX_NESTING = 4
    MAX_BRANCHES = 10
    MAX_LOOPS = 3
    MAX_FUNCS_PER_FILE = 25
    TODO_DENSITY_THRESHOLD = 0.01  # 1 TODO per 100 lines

    # for duplicate function names across repo
    function_name_counts = {}

    # walk repo
    for root, dirs, files in os.walk(project_path):
        # Skip very common heavy/noisy directories
        skip_dirs = {".git", "__pycache__", "venv", ".venv", "node_modules", "dist", "build"}
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for filename in files:
            if not _is_python_file(filename):
                continue

            path = os.path.join(root, filename)
            metrics["files_scanned"] += 1

            source = _safe_read_text(path)
            lines = source.splitlines()
            file_line_count = len(lines)
            metrics["total_lines"] += file_line_count

            # TODO/FIXME count
            todo_in_file = 0
            for line in lines:
                if "TODO" in line or "FIXME" in line:
                    todo_in_file += 1

            # maintainability: large files
            if file_line_count > MAX_FILE_LINES:
                metrics["large_files"] += 1

            # safety/style: count prints by text heuristic (simple + fast)
            # (AST-based print call detection would miss `print` aliased, but is fine.
            # This method is simple and reliable for “do you use prints a lot?”)
            metrics["print_count"] += sum(1 for line in lines if "print(" in line)

            # parse AST
            try:
                tree = ast.parse(source)
            except Exception:
                # If a file can't be parsed (syntax errors, version mismatch),
                # we skip it rather than crashing.
                continue

            # count functions per file for maintainability
            funcs_in_file = 0

            # scan nodes
            for node in ast.walk(tree):
                # wildcard import: from x import *
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name == "*":
                            metrics["wildcard_imports"] += 1
                            break

                # empty except: except ...: pass
                if isinstance(node, ast.ExceptHandler):
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        metrics["empty_except_blocks"] += 1

                # function analysis
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    funcs_in_file += 1
                    metrics["total_functions"] += 1

                    fname = node.name
                    function_name_counts[fname] = function_name_counts.get(fname, 0) + 1

                    # function length: use lineno/end_lineno when available
                    start = getattr(node, "lineno", None)
                    end = getattr(node, "end_lineno", None)

                    if start is None:
                        start = 1
                    if end is None:
                        # fallback: best-effort max lineno in subtree
                        end = start
                        for sub in ast.walk(node):
                            if hasattr(sub, "lineno"):
                                end = max(end, getattr(sub, "lineno"))

                    func_len = (end - start) + 1

                    if func_len > MAX_FUNCTION_LENGTH:
                        metrics["long_functions"] += 1

                    # parameters
                    param_count = len(getattr(node.args, "args", []))
                    if param_count > MAX_PARAMS:
                        metrics["many_param_functions"] += 1

                    # nesting depth
                    nesting = _max_nesting_depth(node)
                    if nesting > MAX_NESTING:
                        metrics["deeply_nested_functions"] += 1

                    # branches and loops (complexity)
                    branch_count = sum(isinstance(n, ast.If) for n in ast.walk(node))
                    loop_count = sum(isinstance(n, (ast.For, ast.While)) for n in ast.walk(node))

                    if branch_count > MAX_BRANCHES:
                        metrics["high_branch_functions"] += 1

                    if loop_count > MAX_LOOPS:
                        metrics["many_loop_functions"] += 1

                    # "god function" heuristic = long + many branches + many params
                    if func_len > 60 and branch_count > MAX_BRANCHES and param_count > MAX_PARAMS:
                        metrics["god_functions"] += 1

            # maintainability: too many functions in file
            if funcs_in_file > MAX_FUNCS_PER_FILE:
                metrics["too_many_functions_files"] += 1

            # maintainability: TODO density (per file)
            # If file has many TODOs relative to size, count it as a “high debt file”
            if file_line_count > 0 and (todo_in_file / file_line_count) > TODO_DENSITY_THRESHOLD:
                metrics["high_todo_density"] += 1

    # duplicates across repo
    # count how many duplicate function “extra occurrences” exist
    dup_extras = 0
    for name, c in function_name_counts.items():
        if c > 1:
            dup_extras += (c - 1)
    metrics["duplicate_function_names"] = dup_extras

    # score + explained suggestions (what/why/how)
    score, breakdown, suggestions = analyze_health(metrics)

    # store + report
    init_db()
    store_scan(project_path, score, suggestions)

    # report file content is generated here; report.py writes it to disk
    generate_report(project_path, score, breakdown, suggestions)

    print(f"\nFinal Health Score: {score}/100")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze.py <path-to-repo>")
        sys.exit(1)
    analyze(sys.argv[1])
