# ansible-inventory
Script to manage your Ansible Inventory and also can be used by ansible as a dynamic inventory source 

## Introduction
The idea is to have a single script that allows you to manage your inventory hosts, groups and variables.

When you have to change a variable that is in several hosts or groups, or you need to change a host that is in several groups, etc., you need to edit several lines of a static file inventory, which is laborious and error prone. With `ansible-inventory` we try to fix these problems and ease the ansible inventory management.

It also includes the idea of host "alias", which will eventually be translated into an ansible group where the only host present will be the host the alias represents.

## Configuration
Currently the `ansible-inventory` configuration is inside the script itself. There are only 3 self explanatory parameters:
* `INVENTORY_PATH`: The path to the inventory file for the `json` backend, currently the only one implemented.
* `HISTORY_FILE`: Path to the file that will store the history of the commands executed in the `ansible-inventory` shell
* `USE_COLORS`: Boolean that selects the usage of colours in the output.

You can configure `ansible-inventory` as the inventory in your `ansible.conf` file so ansible will know about the inventory that you are handling through `ansible-inventory`. This way you wont have to run the commands with `ansible -i /path/to/ansible-inventory`.


# ALPHA STATUS
This software is in an alpha status, there is still a lot of testing to do, documenting and bugfixing. Please do not use in a production environment
