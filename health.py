# health.py

def _tiers(rate, tiers):
    """
    Convert a normalized rate into a penalty using tier thresholds.
    tiers: list of (threshold, penalty) sorted ascending by threshold.
    Example: [(0.2, 0), (0.5, 5), (1.0, 10), (2.0, 18)]
    """
    p = 0
    for threshold, penalty in tiers:
        if rate >= threshold:
            p = penalty
    return p


def analyze_health(metrics):
    total_lines = max(metrics.get("total_lines", 1), 1)
    files = max(metrics.get("files_scanned", 1), 1)
    kloc = max(total_lines / 1000.0, 0.001)  # avoid divide-by-zero

    # --- counts ---
    long_functions = metrics.get("long_functions", 0)
    many_param_functions = metrics.get("many_param_functions", 0)
    deeply_nested = metrics.get("deeply_nested_functions", 0)

    large_files = metrics.get("large_files", 0)
    too_many_funcs_files = metrics.get("too_many_functions_files", 0)
    high_todo_density_files = metrics.get("high_todo_density", 0)
    dup_func_names = metrics.get("duplicate_function_names", 0)

    high_branch = metrics.get("high_branch_functions", 0)
    many_loops = metrics.get("many_loop_functions", 0)
    god_functions = metrics.get("god_functions", 0)

    empty_except = metrics.get("empty_except_blocks", 0)
    wildcard_imports = metrics.get("wildcard_imports", 0)
    print_count = metrics.get("print_count", 0)

    # --- normalize to rates ---
    # per KLOC rates
    long_per_kloc = long_functions / kloc
    params_per_kloc = many_param_functions / kloc
    nest_per_kloc = deeply_nested / kloc

    branch_per_kloc = high_branch / kloc
    loops_per_kloc = many_loops / kloc
    god_per_kloc = god_functions / kloc

    empty_except_per_kloc = empty_except / kloc
    wildcard_per_kloc = wildcard_imports / kloc

    # per-file rates (more stable for file-based issues)
    large_file_rate = (large_files / files) * 100.0                # per 100 files
    too_many_funcs_file_rate = (too_many_funcs_files / files) * 100.0
    todo_debt_file_rate = (high_todo_density_files / files) * 100.0

    # print usage: prints per KLOC (already normalized)
    prints_per_kloc = print_count / kloc

    breakdown = {"readability": 0, "maintainability": 0, "complexity": 0, "safety": 0}
    suggestions = []

    # ----------------------------
    # READABILITY (rate-based)
    # ----------------------------
    # Typical “healthy” codebases should have low long/kloc.
    readability_penalty = 0
    readability_penalty += _tiers(long_per_kloc,   [(0.2, 0), (0.6, 6), (1.2, 12), (2.0, 18)])
    readability_penalty += _tiers(params_per_kloc, [(0.2, 0), (0.6, 4), (1.2, 7), (2.0, 10)])
    readability_penalty += _tiers(nest_per_kloc,   [(0.1, 0), (0.3, 4), (0.8, 8), (1.5, 12)])
    readability_penalty = min(readability_penalty, 30)
    breakdown["readability"] = -readability_penalty

    if long_functions > 0:
        suggestions.append({
            "severity": "MEDIUM" if long_per_kloc >= 0.6 else "LOW",
            "title": "Long functions rate",
            "what": f"{long_functions} long functions detected (~{long_per_kloc:.2f} per KLOC).",
            "why": "Long functions are harder to test and often mix responsibilities.",
            "how": "Split long functions into smaller helpers (input/validation/core logic/output)."
        })

    if deeply_nested > 0:
        suggestions.append({
            "severity": "MEDIUM" if nest_per_kloc >= 0.3 else "LOW",
            "title": "Deep nesting rate",
            "what": f"{deeply_nested} deeply-nested functions (~{nest_per_kloc:.2f} per KLOC).",
            "why": "Deep nesting increases cognitive complexity and bug risk.",
            "how": "Use guard clauses/early returns and extract nested blocks into helpers."
        })

    # ----------------------------
    # MAINTAINABILITY (per-file rate)
    # ----------------------------
    maintainability_penalty = 0
    maintainability_penalty += _tiers(large_file_rate,         [(1.0, 0), (3.0, 6), (6.0, 12), (10.0, 18)])
    maintainability_penalty += _tiers(too_many_funcs_file_rate,[(1.0, 0), (3.0, 5), (6.0, 10), (10.0, 15)])
    maintainability_penalty += _tiers(todo_debt_file_rate,     [(2.0, 0), (5.0, 4), (10.0, 8), (20.0, 12)])
    # duplicates normalized per KLOC (names repeat naturally in big repos; keep low impact)
    maintainability_penalty += _tiers(dup_func_names / kloc,   [(0.5, 0), (1.5, 2), (3.0, 4), (6.0, 6)])
    maintainability_penalty = min(maintainability_penalty, 30)
    breakdown["maintainability"] = -maintainability_penalty

    if large_files > 0:
        suggestions.append({
            "severity": "MEDIUM" if large_file_rate >= 3.0 else "LOW",
            "title": "Large file rate",
            "what": f"{large_files} large files (~{large_file_rate:.1f} per 100 files).",
            "why": "Oversized modules are harder to navigate and typically blend responsibilities.",
            "how": "Split large modules by responsibility (e.g., io.py, parsing.py, services/)."
        })

    if high_todo_density_files > 0:
        suggestions.append({
            "severity": "LOW" if todo_debt_file_rate < 10 else "MEDIUM",
            "title": "Technical-debt markers rate",
            "what": f"{high_todo_density_files} files with high TODO/FIXME density (~{todo_debt_file_rate:.1f} per 100 files).",
            "why": "TODO/FIXME markers represent deferred work and reduce confidence over time.",
            "how": "Convert TODOs into issues and schedule cleanup; remove stale TODOs."
        })

    # ----------------------------
    # COMPLEXITY (rate-based)
    # ----------------------------
    complexity_penalty = 0
    complexity_penalty += _tiers(branch_per_kloc, [(0.2, 0), (0.6, 6), (1.2, 12), (2.0, 18)])
    complexity_penalty += _tiers(loops_per_kloc,  [(0.2, 0), (0.6, 4), (1.2, 8), (2.0, 12)])
    complexity_penalty += _tiers(god_per_kloc,    [(0.05,0), (0.15,8), (0.30,16), (0.60,25)])
    complexity_penalty = min(complexity_penalty, 25)
    breakdown["complexity"] = -complexity_penalty

    if high_branch > 0:
        suggestions.append({
            "severity": "MEDIUM" if branch_per_kloc >= 0.6 else "LOW",
            "title": "High-branch function rate",
            "what": f"{high_branch} high-branch functions (~{branch_per_kloc:.2f} per KLOC).",
            "why": "Many conditional branches create more paths to test and more edge cases.",
            "how": "Extract decision logic, reduce nested ifs, or use a dispatch/lookup table."
        })

    if god_functions > 0:
        suggestions.append({
            "severity": "HIGH",
            "title": "God-function rate",
            "what": f"{god_functions} god functions (~{god_per_kloc:.2f} per KLOC).",
            "why": "God functions are high risk: hard to change safely and tend to accumulate bugs.",
            "how": "Break into cohesive helpers/modules with clear interfaces and responsibilities."
        })

    # ----------------------------
    # SAFETY (rate-based)
    # ----------------------------
    safety_penalty = 0
    safety_penalty += _tiers(empty_except_per_kloc, [(0.02,0), (0.08,8), (0.20,16), (0.40,25)])
    safety_penalty += _tiers(wildcard_per_kloc,     [(0.02,0), (0.06,5), (0.15,10), (0.30,15)])
    safety_penalty += _tiers(prints_per_kloc,       [(2.0, 0), (8.0, 5), (20.0, 10), (40.0, 15)])
    safety_penalty = min(safety_penalty, 25)
    breakdown["safety"] = -safety_penalty

    if empty_except > 0:
        suggestions.append({
            "severity": "HIGH",
            "title": "Empty except blocks rate",
            "what": f"{empty_except} empty except blocks (~{empty_except_per_kloc:.2f} per KLOC).",
            "why": "Swallowing exceptions hides failures and makes debugging much harder.",
            "how": "Log + re-raise, or handle specific exceptions explicitly. Avoid bare except/pass."
        })

    if prints_per_kloc > 2.0:
        suggestions.append({
            "severity": "LOW" if prints_per_kloc < 8 else "MEDIUM",
            "title": "print() usage rate",
            "what": f"{print_count} print() calls (~{prints_per_kloc:.1f} per KLOC).",
            "why": "print() isn’t configurable; logging is better for real tools/services.",
            "how": "Use the logging module with levels and allow verbosity configuration."
        })

    # ----------------------------
    # FINAL SCORE
    # ----------------------------
    total_penalty = -sum(breakdown.values())
    score = max(0, min(100, int(100 - total_penalty)))

    return score, breakdown, suggestions
