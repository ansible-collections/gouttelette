#!/usr/bin/env python3

import argparse
import collections
import io
from pathlib import Path
from typing import Dict, List, Any, Union
import ruamel.yaml
import yaml


class MissingDependency(Exception):
    pass


class ContentInjectionFailure(Exception):
    pass


TaskType = Dict[str, Any]


def _task_to_string(task: TaskType) -> str:
    a = io.StringIO()
    _yaml = ruamel.yaml.YAML()
    _yaml.width = 160  # type: ignore
    _yaml.dump([task], a)
    a.seek(0)
    return a.read().rstrip()


def get_nested_tasks(task: TaskType, target_dir: Path) -> List[TaskType]:
    tasks: List[TaskType] = []
    if "include_tasks" in task:
        tasks += get_tasks(target_dir, play=task["include_tasks"])
    elif "import_tasks" in task:
        tasks += get_tasks(target_dir, play=task["import_tasks"])
    else:
        tasks.append(task)

    return tasks


def get_tasks(target_dir: Path, play: str = "main.yml") -> List[TaskType]:
    tasks: List[TaskType] = []
    current_file = target_dir / play

    data = yaml.load(current_file.read_text(), Loader=yaml.FullLoader)

    for task in data:
        if "include_tasks" in task:
            tasks += get_tasks(target_dir, play=task["include_tasks"])
        elif "import_tasks" in task:
            tasks += get_tasks(target_dir, play=task["import_tasks"])
        elif "block" in task:
            for item in task["block"]:
                tasks += get_nested_tasks(item, target_dir)
        elif "always" in task:
            for item in task["always"]:
                tasks += get_nested_tasks(item, target_dir)
        else:
            tasks.append(task)

    return tasks


def naive_variable_from_jinja2(raw: str) -> Union[None | str]:
    jinja2_string = raw.strip(" }{}")
    if "lookup(" in jinja2_string:
        return None
    if jinja2_string.startswith("not "):
        jinja2_string = jinja2_string[4:]
    variable = jinja2_string.split(".")[0]
    if variable == "item":
        return None
    return variable


def list_dependencies(value: Any) -> List[str]:
    dependencies = []
    if isinstance(value, str):
        if value[0] != "{":
            return []
        variable = naive_variable_from_jinja2(value)
        if variable:
            return [variable]
    for k, v in value.items():
        if isinstance(v, dict):
            dependencies += list_dependencies(v)
        elif isinstance(v, list):
            for i in v:
                dependencies += list_dependencies(i)
        elif not isinstance(v, str):
            pass
        elif "{{" in v:
            variable = naive_variable_from_jinja2(v)
            if variable:
                dependencies.append(variable)
        elif k == "with_items":
            dependencies.append(v.split(".")[0])
    dependencies = [i for i in dependencies if not i.startswith("_")]
    return sorted(list(set(dependencies)))


def extract(tasks: List[TaskType], collection_name: str) -> Dict[str, Any]:
    by_modules: Dict[str, Any] = collections.defaultdict(dict)
    registers: Dict[str, Any] = {}

    for task in tasks:
        if "name" not in task:
            continue

        if task["name"].startswith("_"):
            print(f"Skip task {task['name']} because of the _")
            continue

        depends_on = []
        for r in list_dependencies(value=task):
            if r not in registers:
                raise MissingDependency(
                    f"task: {task['name']}\nCannot find key '{r}' in the known variables: {registers.keys()}"
                )
                continue
            depends_on += registers[r]

        if "register" in task:
            if task["register"].startswith("_"):
                print(f"Hiding register {task['register']} because of the _ prefix.")
                del task["register"]
            else:
                registers[task["register"]] = depends_on + [task]

        if "set_fact" in task:
            for fact_name in task["set_fact"]:
                registers[fact_name] = depends_on + [task]

        module_fqcn = None
        for key in list(task.keys()):
            if key.startswith(collection_name):
                module_fqcn = key
                break
        if not module_fqcn:
            continue

        if module_fqcn not in by_modules:
            by_modules[module_fqcn] = {
                "blocks": [],
            }
        by_modules[module_fqcn]["blocks"] += depends_on + [task]

    return by_modules


def flatten_module_examples(tasks: List[TaskType]) -> str:
    result: str = ""
    seen: List[TaskType] = []

    for task in tasks:
        if task in seen:
            continue
        seen.append(task)
        result += "\n" + _task_to_string(task) + "\n"
    return result


def inject(
    target_dir: Path, extracted_examples: Dict[str, Dict[str, List[Dict[str, Any]]]]
) -> None:
    module_dir = target_dir / "plugins" / "modules"
    for module_fqcn in extracted_examples:
        module_name = module_fqcn.split(".")[-1]
        module_path = module_dir / (module_name + ".py")
        if module_path.is_symlink():
            continue

        examples_section_to_inject = flatten_module_examples(
            extracted_examples[module_fqcn]["blocks"]
        )
        new_content = ""
        in_examples_block = False
        for l in module_path.read_text().split("\n"):
            if l == "EXAMPLES = r'''":
                in_examples_block = True
                new_content += l + "\n" + examples_section_to_inject.lstrip("\n")
            elif in_examples_block and l == "'''":
                in_examples_block = False
                new_content += l + "\n"
            elif in_examples_block:
                continue
            else:
                new_content += l + "\n"
        if in_examples_block:
            raise ContentInjectionFailure(
                "The closing of the EXAMPLES block was not found."
            )
        new_content = new_content.rstrip("\n") + "\n"
        print(f"Updating {module_name}")
        module_path.write_text(new_content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the amazon.cloud modules.")
    parser.add_argument(
        "--target-dir",
        dest="target_dir",
        type=Path,
        default=Path("."),
        help="location of the target repository (default: ./cloud)",
    )

    args = parser.parse_args()
    galaxy_file = args.target_dir / "galaxy.yml"
    galaxy = yaml.safe_load(galaxy_file.open())
    collection_name = f"{galaxy['namespace']}.{galaxy['name']}"
    tasks = []
    test_scenarios_dir = args.target_dir / "tests" / "integration" / "targets"
    for scenario_dir in test_scenarios_dir.glob("*"):
        if not scenario_dir.is_dir():
            continue
        if scenario_dir.name.startswith("setup_"):
            continue
        task_dir = scenario_dir / "tasks"
        tasks += get_tasks(task_dir)

    extracted_examples = extract(tasks, collection_name)
    inject(args.target_dir, extracted_examples)


if __name__ == "__main__":
    main()
