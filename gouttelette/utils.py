#!/usr/bin/env python3


from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, TypedDict, Union
import jinja2
import pkg_resources
import yaml
from pathlib import Path


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
