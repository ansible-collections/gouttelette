#!/usr/bin/env python3


import argparse
import json

import pathlib
import re
import shutil
import subprocess
import pkg_resources
from pbr.version import VersionInfo
from .content_library_data import content_library_static_ds
import baron
import redbaron
import yaml
import json
import copy

from gouttelette.utils import (
    format_documentation,
    indent,
    UtilsBase,
    jinja2_renderer,
    get_module_added_ins,
    python_type,
)

from typing import Dict, Iterable, List, DefaultDict, Union

from .resources import RESOURCES
from .generator import generate_documentation
from .utils import camel_to_snake
from .utils import ignore_description


# vmware specific
def normalize_parameter_name(name):
    # the in-query filter.* parameters are not valid Python variable names.
    # We replace the . with a _ to avoid problem,
    return name.replace("filter.", "filter_")  # < 7.0.2


def ansible_state(operationId, default_operationIds=None):
    mapping = {
        "update": "present",
        "delete": "absent",
        "create": "present",
    }
    # in this case, we don't want to see 'create' in the
    # "Required with" listi
    if (
        default_operationIds
        and operationId == "update"
        and "create" not in default_operationIds
    ):
        return
    if operationId in mapping:
        return mapping[operationId]
    else:
        return operationId


class Description:
    @classmethod
    def normalize(cls, string_list):
        if not isinstance(string_list, list):
            raise TypeError

        with_no_line_break = []
        for l in string_list:
            if "\n" in l:
                with_no_line_break += l.split("\n")
            else:
                with_no_line_break.append(l)

        with_no_line_break = [cls.write_M(i) for i in with_no_line_break]
        with_no_line_break = [cls.write_I(i) for i in with_no_line_break]
        with_no_line_break = [cls.clean_up(i) for i in with_no_line_break]
        return with_no_line_break

    @classmethod
    def clean_up(cls, my_string):
        def rewrite_name(matchobj):
            name = matchobj.group(1)
            snake_name = cls.to_snake(name)
            if snake_name[0] == "#":  # operationId:
                output = f"C({ansible_state(snake_name[1:])})"
            output = f"C({snake_name})"
            return output

        def rewrite_link(matchobj):
            name = matchobj.group(1)
            if "#" in name and name.split("#")[0]:
                output = name.split("#")[1]
            else:
                output = name
            return output

        my_string = my_string.replace(" {@term enumerated type}", "")
        my_string = my_string.replace(" {@term list}", "list")
        my_string = my_string.replace(" {@term operation}", "operation")
        my_string = re.sub(r"{@name DayOfWeek}", "day of the week", my_string)
        my_string = re.sub(r": The\s\S+\senumerated type", ": This option", my_string)
        my_string = re.sub(r" <p> ", " ", my_string)
        my_string = re.sub(r" See {@.*}.", "", my_string)
        my_string = re.sub(r"\({@.*?\)", "", my_string)
        my_string = re.sub(r"{@code true}", "C(True)", my_string)
        my_string = re.sub(r"{@code false}", "C(False)", my_string)
        my_string = re.sub(r"{@code\s+?(.*?)}", r"C(\1)", my_string)
        my_string = re.sub(r"{@param.name\s+?([^}]*)}", rewrite_name, my_string)
        my_string = re.sub(r"{@name\s+?([^}]*)}", rewrite_name, my_string)
        # NOTE: it's pretty much impossible to build something useful
        # automatically.
        # my_string = re.sub(r"{@link\s+?([^}]*)}", rewrite_link, my_string)
        for k in content_library_static_ds:
            my_string = re.sub(k, content_library_static_ds[k], my_string)
        return my_string

    @classmethod
    def to_snake(cls, camel_case):
        camel_case = camel_case.replace("DNS", "dns")
        return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_case).lower()

    @classmethod
    def ref_to_parameter(cls, ref):
        splitted = ref.split(".")
        my_parameter = splitted[-1].replace("-", "_")
        return cls.to_snake(my_parameter)

    @classmethod
    def write_I(cls, my_string):
        refs = {
            cls.ref_to_parameter(i): i
            for i in re.findall(r"[A-Z][\w+]+\.[A-Z][\w+\.-]+", my_string)
        }
        for parameter_name in sorted(refs.keys(), key=len, reverse=True):
            ref = refs[parameter_name]
            my_string = my_string.replace(ref, f"I({parameter_name})")
        return my_string

    @classmethod
    def write_M(cls, my_string):
        my_string = re.sub(r"When operations return.*\.($|\s)", "", my_string)
        m = re.search(r"resource type:\s([a-zA-Z][\w\.]+[a-z])", my_string)
        mapping = {
            "ClusterComputeResource": "vcenter_cluster_info",
            "Datacenter": "vcenter_datacenter_info",
            "Datastore": "vcenter_datastore_info",
            "Folder": "vcenter_folder_info",
            "HostSystem": "vcenter_host_info",
            "Network": "vcenter_network_info",
            "ResourcePool": "vcenter_resourcepool_info",
            "vcenter.StoragePolicy": "vcenter_storage_policies",
            "vcenter.vm.hardware.Cdrom": "vcenter_vm_hardware_cdrom",
            "vcenter.vm.hardware.Disk": "vcenter_vm_hardware_disk",
            "vcenter.vm.hardware.Ethernet": "vcenter_vm_hardware_ethernet",
            "vcenter.vm.hardware.Floppy": "vcenter_vm_hardware_floppy",
            "vcenter.vm.hardware.ParallelPort": "vcenter_vm_hardware_parallel",
            "vcenter.vm.hardware.SataAdapter": "vcenter_vm_hardware_adapter_sata",
            "vcenter.vm.hardware.ScsiAdapter": "vcenter_vm_hardware_adapter_scsi",
            "vcenter.vm.hardware.SerialPort": "vcenter_vm_hardware_serial",
            "VirtualMachine": "vcenter_vm_info",
            "infraprofile.profile": "appliance_infraprofile_configs",
            "appliance.vmon.Service": "appliance_vmon_service",
        }

        if not m:
            return my_string

        resource_name = m.group(1)
        try:
            module_name = mapping[resource_name]
        except KeyError:
            print(f"No mapping for {resource_name}")
            raise

        if f"must be an identifier for the resource type: {resource_name}" in my_string:
            return my_string.replace(
                f"must be an identifier for the resource type: {resource_name}",
                f"must be the id of a resource returned by M(vmware.vmware_rest.{module_name})",
            )
        if f"identifiers for the resource type: {resource_name}" in my_string:
            return my_string.replace(
                f"identifiers for the resource type: {resource_name}",
                f"the id of resources returned by M(vmware.vmware_rest.{module_name})",
            ).rstrip()


def gen_documentation(name, description, parameters, added_ins, next_version):
    
    short_description = description.split(". ")[0]
    documentation = {
        "author": ["Ansible Cloud Team (@ansible-collections)"],
        "description": description,
        "module": name,
        "notes": ["Tested on vSphere 7.0.2"],
        "options": {
            "vcenter_hostname": {
                "description": [
                    "The hostname or IP address of the vSphere vCenter",
                    "If the value is not specified in the task, the value of environment variable C(VMWARE_HOST) will be used instead.",
                ],
                "type": "str",
                "required": True,
            },
            "vcenter_username": {
                "description": [
                    "The vSphere vCenter username",
                    "If the value is not specified in the task, the value of environment variable C(VMWARE_USER) will be used instead.",
                ],
                "type": "str",
                "required": True,
            },
            "vcenter_password": {
                "description": [
                    "The vSphere vCenter password",
                    "If the value is not specified in the task, the value of environment variable C(VMWARE_PASSWORD) will be used instead.",
                ],
                "type": "str",
                "required": True,
            },
            "vcenter_validate_certs": {
                "description": [
                    "Allows connection when SSL certificates are not valid. Set to C(false) when certificates are not trusted.",
                    "If the value is not specified in the task, the value of environment variable C(VMWARE_VALIDATE_CERTS) will be used instead.",
                ],
                "type": "bool",
                "default": True,
            },
            "vcenter_rest_log_file": {
                "description": [
                    "You can use this optional parameter to set the location of a log file. ",
                    "This file will be used to record the HTTP REST interaction. ",
                    "The file will be stored on the host that run the module. ",
                    "If the value is not specified in the task, the value of ",
                    "environment variable C(VMWARE_REST_LOG_FILE) will be used instead.",
                ],
                "type": "str",
            },
            "session_timeout": {
                "description": [
                    "Timeout settings for client session. ",
                    "The maximal number of seconds for the whole operation including connection establishment, request sending and response. ",
                    "The default value is 300s.",
                ],
                "type": "float",
                "version_added": "2.1.0",
            },
        },
        "requirements": ["vSphere 7.0.2 or greater", "python >= 3.6", "aiohttp"],
        "short_description": short_description,
        "version_added": next_version,
    }

    # Note: this series of if block is overcomplicated and should
    # be refactorized.
    for parameter in parameters:
        if parameter["name"] == "action":
            continue
        normalized_name = normalize_parameter_name(parameter["name"])
        description = []
        option = {}
        if parameter.get("required"):
            option["required"] = True
        if parameter.get("aliases"):
            option["aliases"] = parameter.get("aliases")
        if parameter.get("description"):
            description.append(parameter["description"])
        if parameter.get("subkeys"):
            description.append("Valid attributes are:")
            for sub_k, sub_v in parameter.get("subkeys").items():
                sub_v["type"] = python_type(sub_v["type"])
                states = sorted(set([ansible_state(o) for o in sub_v["_operationIds"]]))
                required_with_operations = sorted(
                    set([ansible_state(o) for o in sub_v["_required_with_operations"]])
                )
                description.append(
                    " - C({name}) ({type}): {description} ({states})".format(
                        **sub_v, states=states
                    )
                )
                if required_with_operations:
                    description.append(
                        f"   This key is required with {required_with_operations}."
                    )
                if "enum" in sub_v:
                    description.append("   - Accepted values:")
                    for i in sorted(sub_v["enum"]):
                        description.append(f"     - {i}")
                if "properties" in sub_v:
                    description.append("   - Accepted keys:")
                    for i, v in sub_v["properties"].items():
                        description.append(
                            f"     - {i} ({v['type']}): {v['description']}"
                        )
                        if v.get("enum"):
                            description.append("Accepted value for this field:")
                            for val in sorted(v.get("enum")):
                                description.append(f"       - C({val})")

        option["description"] = list(Description.normalize(description))
        option["type"] = python_type(parameter["type"])
        if "enum" in parameter:
            option["choices"] = sorted(parameter["enum"])
        if parameter["type"] == "array":
            option["elements"] = python_type(parameter["elements"])
        if parameter.get("default"):
            option["default"] = parameter.get("default")

        documentation["options"][normalized_name] = option
        parameter["added_in"] = next_version

    raw_content = pkg_resources.resource_string(
        "vmware_rest_code_generator", "config/modules.yaml"
    )
    module_from_config = get_module_from_config(name, "vmware_rest_code_generator")
    if module_from_config and "documentation" in module_from_config:
        for k, v in module_from_config["documentation"].items():
            documentation[k] = v
    return documentation


def path_to_name(path):
    _path = path.lstrip("/").split("?")[0]
    elements = []
    keys = []
    for i in _path.split("/"):
        if "{" in i:
            keys.append(i)
        elif len(keys) > 1:
            # action for a submodule, we gather these end-points in the main module
            continue
        else:
            elements.append(i)

    # workaround for vcenter_vm_power and appliance_services, appliance_shutdown, appliance_system_storage
    if elements[-1] in (
        "stop",
        "start",
        "restart",
        "suspend",
        "reset",
        "cancel",
        "poweroff",
        "reboot",
        "resize",
    ):
        elements = elements[:-1]
    if elements[0:3] == ["rest", "com", "vmware"]:
        elements = elements[3:]
    elif elements[0:2] == ["rest", "hvc"]:
        elements = elements[1:]
    elif elements[0:2] == ["rest", "appliance"]:
        elements = elements[1:]
    elif elements[0:2] == ["rest", "vcenter"]:
        elements = elements[1:]
    elif elements[0:2] == ["rest", "api"]:
        elements = elements[2:]
    elif elements[:1] == ["api"]:
        elements = elements[1:]

    module_name = "_".join(elements)
    return module_name.replace("-", "")


def gen_arguments_py(parameters, list_index=None):
    result = ""
    for parameter in parameters:
        name = normalize_parameter_name(parameter["name"])
        values = []

        if name in ["user_name", "username", "encryption_key", "client_token"]:
            values.append("'no_log': True")
        elif "password" in name:
            values.append("'no_log': True")

        if parameter.get("required"):
            values.append("'required': True")

        aliases = parameter.get("aliases")
        if aliases:
            values.append(f"'aliases': {aliases}")

        _type = python_type(parameter["type"])
        values.append(f"'type': '{_type}'")
        if "enum" in parameter:
            choices = ", ".join([f"'{i}'" for i in sorted(parameter["enum"])])
            values.append(f"'choices': [{choices}]")
        if python_type(parameter["type"]) == "list":
            _elements = python_type(parameter["elements"])
            values.append(f"'elements': '{_elements}'")

        # "bus" option defaulting on 0
        if name == "bus":
            values.append("'default': 0")
        elif "default" in parameter:
            default = parameter["default"]
            values.append(f"'default': '{default}'")

        result += f"\nargument_spec['{name}'] = "
        result += "{" + ", ".join(values) + "}"
    return result


def flatten_ref(tree, definitions):
    if isinstance(tree, str):
        if tree.startswith("#/definitions/"):
            raise Exception("TODO")
        return definitions.get(tree)
    if isinstance(tree, list):
        return [flatten_ref(i, definitions) for i in tree]
    if tree is None:
        return {}
    for k in tree:
        v = tree[k]
        if k == "$ref":
            dotted = v.split("/")[2]
            if dotted in ["vapi.std.localization_param", "VapiStdLocalizationParam"]:
                # to avoid an endless loop with
                # vapi.std.nested_localizable_message
                return {"go_to": "vapi.std.localization_param"}
            definition = definitions.get(dotted)
            data = flatten_ref(definition, definitions)
            if "description" not in data and "description" in tree:
                data["description"] = tree["description"]
            return data
        elif isinstance(v, dict):
            tree[k] = flatten_ref(v, definitions)
        else:
            pass
    return tree


class Resource:
    def __init__(self, name):
        self.name = name
        self.operations = {}
        self.summary = {}


# amazon.cloud specific    
def generate_params(definitions: Iterable) -> str:
    params: str = ""
    keys = sorted(
        definitions.keys() - ["wait", "wait_timeout", "state", "purge_tags", "force"]
    )
    for key in keys:
        params += f"\nparams['{key}'] = module.params.get('{key}')"

    return params


def gen_mutually_exclusive(schema: Dict) -> List:
    primary_idenfifier = schema.get("primaryIdentifier", [])
    entries: List = []

    if len(primary_idenfifier) > 1:
        entries.append([tuple(primary_idenfifier), "identifier"])

    return entries


def ensure_all_identifiers_defined(schema: Dict) -> str:
    primary_idenfifier = schema.get("primaryIdentifier", [])
    new_content: str = "if state in ('present', 'absent', 'get', 'describe') and module.params.get('identifier') is None:\n"
    new_content += 8 * " "
    new_content += f"if not module.params.get('{primary_idenfifier[0]}')" + " ".join(
        map(lambda x: f" or not module.params.get('{x}')", primary_idenfifier[1:])
    )
    new_content += ":\n" + 12 * " "
    new_content += (
        "module.fail_json(f'You must specify both {*identifier, } identifiers.')\n"
    )

    return new_content


def generate_argument_spec(options: Dict) -> str:
    argument_spec: str = ""
    options_copy = copy.deepcopy(options)

    for key in options_copy.keys():
        ignore_description(options_copy[key])

    for key in options_copy.keys():
        argument_spec += f"\nargument_spec['{key}'] = "
        argument_spec += str(options_copy[key])

    argument_spec = argument_spec.replace("suboptions", "options")

    return argument_spec


class AnsibleModule(UtilsBase):
    template_file = "default_module.j2"

    def __init__(self, schema: Iterable):
        self.schema = schema
        self.name = self.generate_module_name()

    def generate_module_name(self):
        splitted = self.schema.get("typeName").split("::")
        prefix = splitted[1].lower()
        list_to_str = "".join(map(str, splitted[2:]))
        return prefix + "_" + camel_to_snake(list_to_str)

    def renderer(self, target_dir: str, next_version: str):
        added_ins = get_module_added_ins(self.name, git_dir=target_dir / ".git")
        documentation = generate_documentation(
            self,
            added_ins,
            next_version,
        )

        arguments = generate_argument_spec(documentation["options"])
        documentation_to_string = format_documentation(documentation)
        content = jinja2_renderer(
            self.template_file,
            "amazon_cloud_code_generator",
            arguments=indent(arguments, 4),
            documentation=documentation_to_string,
            name=self.name,
            resource_type=f"'{self.schema.get('typeName')}'",
            params=indent(generate_params(documentation["options"]), 4),
            primary_identifier=self.schema["primaryIdentifier"],
            required_if=gen_required_if(self.schema),
            mutually_exclusive=gen_mutually_exclusive(self.schema),
            ensure_all_identifiers_defined=ensure_all_identifiers_defined(self.schema)
            if len(self.schema["primaryIdentifier"]) > 1
            else "",
            create_only_properties=self.schema.get("createOnlyProperties", {}),
            handlers=list(self.schema.get("handlers", {}).keys()),
        )

        self.write_module(target_dir, content)

# common procs
def gen_required_if(self, schema: Union[List, Dict]) -> List:
    if isinstance(schema, dict):
        primary_idenfifier = schema.get("primaryIdentifier", [])
        required = schema.get("required", [])
        entries: List = []
        states = ["absent", "get"]

        _primary_idenfifier = copy.copy(primary_idenfifier)

        # For compound primary identifiers consisting of multiple resource properties strung together,
        # use the property values in the order that they are specified in the primary identifier definition
        if len(primary_idenfifier) > 1:
            entries.append(["state", "list", primary_idenfifier[:-1], True])
            _primary_idenfifier.append("identifier")

        entries.append(
            [
                "state",
                "present",
                list(set([*_primary_idenfifier, *required])),
                True,
            ]
        )
        [entries.append(["state", state, _primary_idenfifier, True]) for state in states]
    else:
        by_states = DefaultDict(list)
        for parameter in schema:
            for operation in parameter.get("_required_with_operations", []):
                by_states[ansible_state(operation)].append(parameter["name"])
        entries = []
        for operation, fields in by_states.items():
            state = ansible_state(operation)
            if "state" in entries:
                entries.append(["state", state, sorted(set(fields)), True])

    return entries


def main():
    parser = argparse.ArgumentParser(description="Build the amazon.cloud modules.")
    parser.add_argument(
        "--target-dir",
        dest="target_dir",
        type=pathlib.Path,
        default=pathlib.Path("cloud"),
        help="location of the target repository (default: ./cloud)",
    )
    parser.add_argument(
        "--next-version",
        type=str,
        default="TODO",
        help="the next major version",
    )
    parser.add_argument(
        "--schema-dir",
        type=pathlib.Path,
        default=pathlib.Path("amazon_cloud_code_generator/api_specifications"),
        help="location where to store the collected schemas (default: ./amazon_cloud_code_generator/api_specifications)",
    )
    args = parser.parse_args()

    module_list = []

    for type_name in RESOURCES:
        print(f"Generating modules {type_name}")
        schema_file = args.schema_dir / f"{type_name}.json"
        schema = json.loads(schema_file.read_text())

        module = AnsibleModule(schema=schema)

        if module.is_trusted("amazon_cloud_code_generator"):
            module.renderer(target_dir=args.target_dir, next_version=args.next_version)
            module_list.append(module.name)

    modules = [f"plugins/modules/{module}.py" for module in module_list]
    module_utils = ["plugins/module_utils/core.py", "plugins/module_utils/utils.py"]

    ignore_dir = args.target_dir / "tests" / "sanity"
    ignore_dir.mkdir(parents=True, exist_ok=True)

    for version in ["2.9", "2.10", "2.11", "2.12", "2.13", "2.14"]:
        per_version_ignore_content = ""
        skip_list = []

        if version in ["2.9", "2.10", "2.11"]:
            skip_list += [
                "compile-2.7!skip",  # Py3.6+
                "compile-3.5!skip",  # Py3.6+
                "import-2.7!skip",  # Py3.6+
                "import-3.5!skip",  # Py3.6+
                "future-import-boilerplate!skip",  # Py2 only
                "metaclass-boilerplate!skip",  # Py2 only
                "compile-2.6!skip",  # Py3.6+
                "import-2.6!skip",  # Py3.6+
            ]
        validate_skip_needed = [
            "plugins/modules/s3_bucket.py",
            "plugins/modules/backup_backup_vault.py",
            "plugins/modules/backup_framework.py",
            "plugins/modules/backup_report_plan.py",
            "plugins/modules/lambda_function.py",
            "plugins/modules/rdsdb_proxy.py",
            "plugins/modules/redshift_cluster.py",
            "plugins/modules/eks_cluster.py",
            "plugins/modules/dynamodb_global_table.py",
            "plugins/modules/kms_replica_key.py",
            "plugins/modules/rds_db_proxy.py",
            "plugins/modules/iam_server_certificate.py",
            "plugins/modules/cloudtrail_trail.py",
            "plugins/modules/route53_key_signing_key.py",
            "plugins/modules/redshift_endpoint_authorization.py",
            "plugins/modules/eks_fargate_profile.py",
        ]
        mutually_exclusive_skip = [
            "plugins/modules/eks_addon.py",
            "plugins/modules/eks_fargate_profile.py",
            "plugins/modules/redshift_endpoint_authorization.py",
            "plugins/modules/route53_key_signing_key.py",
        ]

        for f in module_utils:
            for skip in skip_list:
                per_version_ignore_content += f"{f} {skip}\n"

        for f in modules:
            for skip in skip_list:
                per_version_ignore_content += f"{f} {skip}\n"

            if f in validate_skip_needed:
                if version in ["2.10", "2.11", "2.12", "2.13", "2.14"]:
                    if (
                        f == "plugins/modules/redshift_endpoint_authorization.py"
                        and version in ("2.11", "2.12", "2.13", "2.14")
                    ):
                        pass
                    else:
                        validate_skip_list = [
                            "validate-modules:no-log-needed",
                        ]
                        for skip in validate_skip_list:
                            per_version_ignore_content += f"{f} {skip}\n"

            if version in ["2.10", "2.11", "2.12", "2.13", "2.14"]:
                per_version_ignore_content += (
                    f"{f} validate-modules:parameter-state-invalid-choice\n"
                )

        for f in mutually_exclusive_skip:
            per_version_ignore_content += (
                f"{f} validate-modules:mutually_exclusive-type\n"
            )

        ignore_file = ignore_dir / f"ignore-{version}.txt"
        ignore_file.write_text(per_version_ignore_content)

    meta_dir = args.target_dir / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    yaml_dict = {
        "requires_ansible": """>=2.11.0""",
        "action_groups": {"aws": []},
        "plugin_routing": {"modules": {}},
    }
    for m in module_list:
        yaml_dict["action_groups"]["aws"].append(m)

    yaml_dict["plugin_routing"]["modules"].update(
        {
            "rdsdb_proxy": {"redirect": "amazon.cloud.rds_db_proxy"},
            "s3_object_lambda_access_point": {
                "redirect": "amazon.cloud.s3objectlambda_access_point"
            },
            "s3_object_lambda_access_point_policy": {
                "redirect": "amazon.cloud.s3objectlambda_access_point_policy"
            },
        }
    )
    yaml_dict["action_groups"]["aws"].extend(
        [
            "rdsdb_proxy",
            "s3_object_lambda_access_point",
            "s3_object_lambda_access_point_policy",
        ]
    )

    runtime_file = meta_dir / "runtime.yml"
    with open(runtime_file, "w") as file:
        yaml.safe_dump(yaml_dict, file, sort_keys=False)

    info = VersionInfo("amazon_cloud_code_generator")
    dev_md = args.target_dir / "dev.md"
    dev_md.write_text(
        (
            "The modules are autogenerated by:\n"
            "https://github.com/ansible-collections/amazon_cloud_code_generator\n"
            ""
            f"version: {info.version_string()}\n"
        )
    )
    dev_md = args.target_dir / "commit_message"
    dev_md.write_text(
        (
            "bump auto-generated modules\n"
            "\n"
            "The modules are autogenerated by:\n"
            "https://github.com/ansible-collections/amazon_cloud_code_generator\n"
            ""
            f"version: {info.version_string()}\n"
        )
    )

    collection_dir = pkg_resources.resource_filename(
        "amazon_cloud_code_generator", "data"
    )
    print(f"Copying collection from {collection_dir}")
    shutil.copytree(collection_dir, args.target_dir, dirs_exist_ok=True)


if __name__ == "__main__":
    main()
