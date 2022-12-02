#!/usr/bin/env python3

from gouttelette import utils


def test_format_documentaion():
    input_arg = {
        "author": "Ansible Cloud Team (@ansible-collections)",
        "description": [
            "Creates and manages a metric stream.",
        ],
        "extends_documentation_fragment": ["amazon.aws.aws", "amazon.aws.ec2"],
        "module": "cloudwatch_metric_stream",
        "options": {
            "exclude_filters": {
                "description": [
                    "This structure defines the metrics that will be streamed."
                ],
                "elements": "dict",
                "suboptions": {
                    "namespace": {
                        "description": [
                            "Only metrics with Namespace matching this value will be streamed."
                        ],
                        "type": "str",
                    }
                },
                "type": "list",
            },
        },
    }
    output = "r'''\nmodule: cloudwatch_metric_stream\nshort_description: Creates and manages a metric stream\ndescription:\n- Creates and manages a metric stream.\noptions:\n    exclude_filters:\n        description:\n        - This structure defines the metrics that will be streamed.\n        elements: dict\n        suboptions:\n            namespace:\n                description:\n                - Only metrics with Namespace matching this value will be streamed.\n                type: str\n        type: list\n'''"
    assert utils.format_documentation(input_arg) == output
