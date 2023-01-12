# Gouttelette
## _Cloud Content Code Generator_

This repository contains the `gouttelette` package, a well tested python libraries that generates the cloud collections [``amazon.cloud``](https://github.com/ansible-collections/amazon.cloud) and [``vmware.vmware_rest``](https://github.com/ansible-collections/vmware.vmware_rest).

This tool reuses the functionalities of the existing [amazon_cloud_code_generator](https://github.com/ansible-collections/amazon_cloud_code_generator) and [vmware_rest_code_generator](https://github.com/ansible-collections/vmware_rest_code_generator). These generators will be archived in the future.

The final goal is to integrate this tool with the [``content_builder``](https://github.com/ansible-community/ansible.content_builder)
and extend the usage to other openAPI based cloud platforms.

## Requirements

The `amazon.cloud` modules generation relies on the CloudFormation client. Hence, the following requirements must be met:
- `boto3 >= 1.20.0`
- `botocore >= 1.23.0`

Apart from the above requirements, the tool needs

- `Python 3.9`
- `tox`

### Usage

The ``gouttelette`` generator is capable of performing the following functionalities

- [`refresh_modules`](https://github.com/ansible-collections/gouttelette/blob/main/gouttelette/cmd/refresh_modules.py) : Generates the modules specified in [resources.py](https://github.com/ansible-collections/gouttelette/blob/main/gouttelette/cmd/resources.py). It is important to make sure the rest schema and modules list files are present in the default location (details below), if not passed as input arguments.
```
  python -m gouttelette.cmd.refresh_modules --collection <collection_name> --target-dir <path> --modules <path> --next-version <version> --schema-dir <path>
```

| Input args | Description  |
| ------ | ------ |
| collection | The collection for which the modules are generated (values: amazon_cloud or vmware_rest, default: amazon_cloud) |
| target-dir | Location of the target repository (default: ./cloud or ./vmware_rest) |
| modules | Location of the [modules.yaml](https://github.com/ansible-collections/gouttelette/blob/main/gouttelette/config/amazon_cloud/modules.yaml) file (default: gouttelette/config/<collection>)|
| next-version | The next major version (default: "TODO" |
| schema-dir | Location of the collected schemas (default: ./gouttelette/api_specifications/<collection> |

- [`refresh_schema`](https://github.com/ansible-collections/gouttelette/blob/main/gouttelette/cmd/refresh_schema.py): This command is for the amazon.cloud . It uses the AWS CloudFormation API to generate the rest schemas for the modules mentioned in the modules.yaml.
```
  python -m gouttelette.cmd.refresh_schema  --schema-dir <path>
```
| Input args | Description  |
| ------ | ------ |
| schema-dir | Location where the generated schemas will be stored (default: ./gouttelette/api_specifications/amazon_cloud |

- [`refresh_examples`](https://github.com/ansible-collections/gouttelette/blob/main/gouttelette/cmd/refresh_examples.py): Generates the examples by executing the integration tests and populates the EXAMPLE block of the module documentation.
```
  python -m gouttelette.cmd.refresh_examples  --target-dir <path>
```
| Input args | Description  |
| ------ | ------ |
| target-dir | Location of the target repository (default: ./cloud or ./vmware_rest). This location should have the generated modules. |

- [`refresh_ignore_files`](https://github.com/ansible-collections/gouttelette/blob/main/gouttelette/cmd/refresh_ignore_files.py): Refresh the ignore files of the vmware_rest collection.
```
  python -m gouttelette.cmd.refresh_ignore_files  --target-dir <path>
```
| Input args | Description  |
| ------ | ------ |
| target-dir | Location of the target repository (default: ./cloud or ./vmware_rest). This location should have the generated modules. |

### _Refresh modules from gouttelette_

- Clone [``gouttelette repo ``](https://github.com/ansible-collections/gouttelette/blob/main/gouttelette).
```
git clone https://github.com/ansible-collections/gouttelette
```
- From gouttelette execute the following command
```
python -m gouttelette.cmd.refresh_modules --collection "amazon_cloud"
```
The default values are taken for the other input arguments.
Same steps are followed to refresh schema , refresh examples and refresh ignore files.

### _Referesh modules from amazon.cloud or vmware.vmware_rest_

- Clone the collection repository
```
mkdir -p ~/.ansible/collections/ansible_collections/vmware/vmware_rest
cd ~/.ansible/collections/ansible_collections/vmware/vmware_rest
git clone https://github.com/ansible-collections/vmware.vmware_rest
tox -e refresh_modules
``` 

We can specify the version
```
tox -e refresh_modules --vetsion "2.0.0"
```
## Contributing
We welcome community contributions and if you find problems, please open an issue or create a Pull Request. You can also join us in the:
    - `#ansible-aws` [irc.libera.chat](https://libera.chat/) channel
    - `#ansible` (general use questions and support), `#ansible-community` (community and collection development questions), and other [IRC channels](https://docs.ansible.com/ansible/devel/community/communication.html#irc-channels).

The Amazon Web Services Working groups is holding a monthly community meeting at `#ansible-aws` IRC channel at 17:30 UTC every fourth Thursday of the month. If you have something to discuss (e.g. a PR that needs help), add your request to the [meeting agenda](https://github.com/ansible/community/issues/654) and join the IRC `#ansible-aws` channel. Invite (import by URL): [ics file](https://raw.githubusercontent.com/ansible/community/main/meetings/ical/aws.ics)

You don't know how to start? Refer to our [contribution guide](CONTRIBUTING.md)!

## Code of Conduct

This project is governed by the [Ansible Community code of conduct](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html)

## Licensing

GNU General Public License v3.0 or later.

See [COPYING](https://www.gnu.org/licenses/gpl-3.0.txt) to see the full text.
