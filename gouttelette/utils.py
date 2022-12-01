#!/usr/bin/env python3


import jinja2
import yaml

def jinja2_renderer(template_file, generator, **kwargs):
    templateLoader = jinja2.PackageLoader(generator)
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template(template_file)
    return template.render(kwargs)

def format_documentation(documentation):
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
