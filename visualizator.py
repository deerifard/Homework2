import os
import zlib
import argparse
from pathlib import Path
import subprocess


def read_git_object(repo_path, object_hash):
    obj_path = os.path.join(repo_path, ".git", "objects", object_hash[:2], object_hash[2:])
    if not os.path.exists(obj_path):
        raise FileNotFoundError(f"Объект {object_hash} не найден по пути {obj_path}")
    with open(obj_path, "rb") as file:
        compressed_data = file.read()
        decompressed_data = zlib.decompress(compressed_data)
    return decompressed_data


def parse_commit_object(repo_path, commit_hash):
    commit_data = read_git_object(repo_path, commit_hash)
    _, content = commit_data.split(b"\x00", 1)
    lines = content.decode().split("\n")

    tree_hash = next(line.split()[1] for line in lines if line.startswith("tree"))
    parent_hashes = [line.split()[1] for line in lines if line.startswith("parent")]
    files = get_files_from_tree(repo_path, tree_hash)

    return {
        "tree": tree_hash,
        "parents": parent_hashes,
        "files": files,
    }


def get_files_from_tree(repo_path, tree_hash, path_prefix=""):
    tree_data = read_git_object(repo_path, tree_hash)
    _, content = tree_data.split(b"\x00", 1)
    files = []
    while content:
        null_idx = content.index(b"\x00")
        mode_name = content[:null_idx].decode()
        obj_hash = content[null_idx + 1 : null_idx + 21].hex()
        content = content[null_idx + 21 :]
        mode, name = mode_name.split(" ", 1)
        full_path = f"{path_prefix}/{name}" if path_prefix else name
        if mode == "40000":  # Дерево (папка)
            files.extend(get_files_from_tree(repo_path, obj_hash, full_path))
        else:  # Блоб (файл)
            files.append(full_path)
    return files


def get_commits(repo_path, branch_name):
    ref_path = Path(repo_path, ".git", "refs", "heads", branch_name)
    if not ref_path.exists():
        raise FileNotFoundError(f"Ветка {branch_name} не найдена: {ref_path}")
    head_ref = ref_path.read_text().strip()

    commits = []
    to_visit = [head_ref]
    seen = set()

    while to_visit:
        commit_hash = to_visit.pop()
        if commit_hash in seen:
            continue
        seen.add(commit_hash)
        commit = parse_commit_object(repo_path, commit_hash)
        commits.append({
            "hash": commit_hash,
            "files": commit["files"],
        })
        to_visit.extend(commit["parents"])

    return commits


def parse_commits(commits):
    graph = {}
    for commit in commits:
        commit_hash = commit["hash"]
        files = commit["files"]
        for file in files:
            if file not in graph:
                graph[file] = []
            graph[file].append(commit_hash)
    return graph


def generate_mermaid(graph):
    lines = ["graph TD"]  # Начинаем с директивы для Mermaid

    for node, dependencies in graph.items():
        # Экранируем узлы, но убираем ненужные кавычки
        safe_node = node.replace('"', '\\"')
        for dep in dependencies:
            # Также экранируем зависимости
            safe_dep = dep.replace('"', '\\"')
            # Генерируем корректный синтаксис Mermaid
            lines.append(f'    {safe_node} --> {safe_dep}')

    return "\n".join(lines)  # Возвращаем синтаксический граф


def save_mermaid_to_png(mermaid_code, output_path, mermaid_cli_path):
    temp_file = "temp.mmd"
    with open(temp_file, "w") as file:
        file.write(mermaid_code)

    try:
        subprocess.run(
            [mermaid_cli_path, "-i", temp_file, "-o", output_path],
            shell=True
        )
    finally:
        os.remove(temp_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Генерация графа зависимостей файлов в ветке репозитория Git.")
    parser.add_argument("repo_path", help="Путь до Git репозитория")
    parser.add_argument("mermaid_cli_path", help="Путь до исполняемого файла mermaid-cli")
    parser.add_argument("branch_name", help="Название ветки")
    parser.add_argument("output_path", help="Путь для сохранения результата (PNG)")

    args = parser.parse_args()

    repo_path = args.repo_path
    mermaid_cli_path = args.mermaid_cli_path
    branch_name = args.branch_name
    output_path = args.output_path

    commits = get_commits(repo_path, branch_name)
    graph = parse_commits(commits)
    mermaid_code = generate_mermaid(graph)
    save_mermaid_to_png(mermaid_code, output_path, mermaid_cli_path)

    print("Граф зависимостей сохранён в:", output_path)
