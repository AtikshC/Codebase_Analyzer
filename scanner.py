import os

def find_python_files(base_path):
    py_files = []

    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))

    return py_files
