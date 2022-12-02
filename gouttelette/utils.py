#!/usr/bin/env python3


from typing import Dict, Iterable, List, Optional, TypedDict
import jinja2
import yaml
import pkg_resources


def jinja2_renderer(template_file, generator, **kwargs):
    templateLoader = jinja2.PackageLoader(generator)
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template(template_file)
    return template.render(kwargs)


def format_documentation(documentation: Iterable) -> str:
    yaml.Dumper.ignore_aliases = lambda *args: True

    def _sanitize(input):
        if isinstance(input, str):
            return input.replace("':'", ":")
        if isinstance(input, list):
            return [l.replace("':'", ":") for l in input]
        if isinstance(input, dict):
            return {k: _sanitize(v) for k, v in input.items()}
        if isinstance(input, bool):
            return input
        raise TypeError

    import q

    q(documentation)
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
            q(sanitized)
        else:
            sanitized = documentation[i]
        final += yaml.dump({i: sanitized}, indent=4, default_flow_style=False)
    final += "'''"
    q(final)
    return final


def indent(text_block: str, indent: int = 0) -> str:
    result: str = ""

    for line in text_block.split("\n"):
        result += " " * indent
        result += line
        result += "\n"
    return result


def get_module_from_config(module: str, generator: str):
    raw_content = pkg_resources.resource_string(generator, "config/modules.yaml")
    for i in yaml.safe_load(raw_content):
        if module in i:
            return i[module]
    return False


def python_type(value) -> str:
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


class UtilsBase:
    def is_trusted(self, generator: str) -> bool:
        if get_module_from_config(self.name, generator) is False:
            print(f"- do not build: {self.name}")
        else:
            return True

    def write_module(self, target_dir: str, content: str):
        module_dir = target_dir / "plugins" / "modules"
        module_dir.mkdir(parents=True, exist_ok=True)
        module_py_file = module_dir / "{name}.py".format(name=self.name)
        module_py_file.write_text(content)
