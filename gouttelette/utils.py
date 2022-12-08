#!/usr/bin/env python3


from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, TypedDict, Union
import jinja2
import pkg_resources
import yaml
from pathlib import Path
from functools import lru_cache


def jinja2_renderer(
    template_file: str, generator: str, **kwargs: Dict[str, Any]
) -> str:
    templateLoader = jinja2.PackageLoader(generator)
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template(template_file)
    return template.render(kwargs)


def format_documentation(documentation: Any) -> str:
    yaml.Dumper.ignore_aliases = lambda *args: True  # type: ignore

    def _sanitize(input: Any) -> Any:
        if isinstance(input, str):
            return input.replace("':'", ":")
        if isinstance(input, list):
            return [l.replace("':'", ":") for l in input]
        if isinstance(input, dict):
            return {k: _sanitize(v) for k, v in input.items()}
        if isinstance(input, bool):
            return input
        raise TypeError

    keys = [
        "module",
        "short_description",
        "description",
        "options",
        "author",
        "version_added",
        "requirements",
        "extends_documentation_fragment",
        "seealso",
        "notes",
    ]
    final = "r'''\n"
    for i in keys:
        if i not in documentation:
            continue
        if isinstance(documentation[i], str):
            sanitized = _sanitize(documentation[i])
        else:
            sanitized = documentation[i]
        final += yaml.dump({i: sanitized}, indent=4, default_flow_style=False)
    final += "'''"
    return final


def indent(text_block: str, indent: int = 0) -> str:
    result: str = ""

    for line in text_block.split("\n"):
        result += " " * indent
        result += line
        result += "\n"
    return result


def get_module_from_config(module: str, generator: str) -> dict[str, Any]:

    raw_content = pkg_resources.resource_string(generator, "config/modules.yaml")
    for i in yaml.safe_load(raw_content):
        if module in i:
            return i[module] or {}
    raise KeyError


def python_type(value: str) -> str:
    TYPE_MAPPING = {
        "array": "list",
        "boolean": "bool",
        "integer": "int",
        "number": "int",
        "object": "dict",
        "string": "str",
    }
    if isinstance(value, list):
        return TYPE_MAPPING.get(value[0], value)
    return TYPE_MAPPING.get(value, value)


def run_git(git_dir: str, *args):
    cmd = [
        "git",
        "--git-dir",
        git_dir,
    ]
    for arg in args:
        cmd.append(arg)
    r = subprocess.run(cmd, text=True, capture_output=True)
    return r.stdout.rstrip().split("\n")


@lru_cache(maxsize=None)
def file_by_tag(git_dir: str) -> Dict:
    tags = run_git(git_dir, "tag")

    files_by_tag: Dict = {}
    for tag in tags:
        files_by_tag[tag] = run_git(git_dir, "ls-tree", "-r", "--name-only", tag)

    return files_by_tag


def get_module_added_ins(module_name: str, git_dir: str) -> Dict:
    added_ins = {"module": None, "options": {}}
    module = f"plugins/modules/{module_name}.py"

    for tag, files in file_by_tag(git_dir).items():
        if "rc" in tag:
            continue
        if module in files:
            if not added_ins["module"]:
                added_ins["module"] = tag
            content = "\n".join(
                run_git(
                    git_dir,
                    "cat-file",
                    "--textconv",
                    f"{tag}:{module}",
                )
            )
            try:
                ast_file = redbaron.RedBaron(content)
            except baron.BaronError as e:
                print(f"Failed to parse {tag}:plugins/modules/{module_name}.py. {e}")
                continue
            doc_block = ast_file.find(
                "assignment", target=lambda x: x.dumps() == "DOCUMENTATION"
            )
            if not doc_block or not doc_block.value:
                print(f"Cannot find DOCUMENTATION block for module {module_name}")
            doc_content = yaml.safe_load(doc_block.value.to_python())
            for option in doc_content["options"]:
                if option not in added_ins["options"]:
                    added_ins["options"][option] = tag

    return added_ins


@dataclass
class UtilsBase:
    name: str

    def is_trusted(self, generator: str) -> bool:
        try:
            get_module_from_config(self.name, generator)
            return True
        except KeyError:
            print(f"- do not build: {self.name}")
            return False

    def write_module(self, target_dir: Path, content: str) -> None:
        module_dir = target_dir / "plugins" / "modules"
        module_dir.mkdir(parents=True, exist_ok=True)
        module_py_file = module_dir / "{name}.py".format(name=self.name)
        module_py_file.write_text(content)
