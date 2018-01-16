# ansible-inventory
Script to manage your Ansible Inventory and also can be used by ansible as a dynamic inventory source


![demo](http://i.imgur.com/ULCWQgm.gif)

**NOTE**: Due to ansible including now an executable called `ansible-inventory`, the `ansible-inventory` executable has been **renamed** to `ansible-inv`


## Introduction
The idea is to have a single script that allows you to manage your inventory hosts, groups and variables.

When you have to change a variable that is in several hosts or groups, or you need to change a host that is in several groups, etc., you need to edit several lines of a static file inventory, which is laborious and error prone. With `ansible-inventory` we try to fix these problems and ease the ansible inventory management.

## Features

 * Multiple backends: redis, file. ( may add more in the future )
 * Concurrent users support
 * Interactive console
 * Autocompletion
 * Tree display for groups
 * Multiple deploy support ( production, development, etc )
 * Coloured information to visually match a host, var, group, etc with an specific color.
 * Import inventories in the [ansible json format]( http://docs.ansible.com/ansible/dev_guide/developing_inventory.html )

## Installation
Ansible Inventory requires python3. In case you want to use the `redis` backend, you will also need to install [redis-py]( https://github.com/andymccurdy/redis-py ) (`sudo apt-get install python3-redis`).

You can install `ansible-inventory` using `pip3` 

```
pip3 install ansible-inventory
``` 

You can also just download the `ansible-inventory` script and place it wherever you want inside your `PATH`.

The first time you execute the script, it will create the necesary directories and default configurations inside your user's `HOME`.

## Upgrade

You can upgrade `ansible-inventory` using `pip3`

```
pip3 install -U ansible-inventor
```

## Configuration
This is the default Ansible Inventory configuration. Not many options and I believe it is quite self-explanatory:

```
[ global]
use_colors = True

# backend: redis, file
backend = file

[ file_backend]
path = ~/.ansible/inventory.json

[ redis_backend]
host =
port =
password =
inventory_name =
```

Currently you can choose between 2 backends:

 * **file_backend**: It uses a file to store the inventory in json format.
 * **redis_backend**: It uses redis to store the inventory in a variable in json format. Note that you will need to enable redis AOF to have persistence. More in the [redis persistence documentation]( http://redis.io/topics/persistence ).

Both backends support concurrency, although in the case of Redis, the concurrency is limited to a single master scenario for now.

You can configure `ansible-inventory` as the inventory in your `ansible.cfg` file so ansible will know about the inventory that you are handling through `ansible-inventory`. This way you wont have to run the commands with `ansible -i /path/to/ansible-inv`. To do this, edit your ansible configuration file in `/etc/ansible/ansible.cfg` or `~/.ansible.cfg` and congiure your inventory like this:

```
[defaults]

inventory = /path/to/ansible-inv

...
```

## Importing an existing inventory

Ansible Inventory also allows you to import an existing inventory as long as it uses the [ansible json format](http://docs.ansible.com/ansible/developing_inventory.html).
So lets say that you dumped your inventory to a json file called `inventory.json`. You can import it just like this:

```
ansible-inv --import inventory.json
```

## Deploying for multiple environments

Ansible Inventory has an special behaviour. When you symlink the script and then execute it via symlink, it will use the directory where the symlink is placed as its HOME directory. This way you can have different environments with different configuration files.

For example, you may have this ansible structure:

```
inventories/
    development/
       group_vars/
       host_vars/
       hosts --> /usr/local/bin/ansible-inv (symlink)
       .ansible/
          ansible-inventory.cfg
          ansible-inventory_history

    production/
       group_vars/
       host_vars/
       hosts --> /usr/local/bin/ansible-inv (symlink)
       .ansible/
          ansible-inventory.cfg
          ansible-inventory_history

roles/
[ ... ]
```

Note that here _hosts_ is a symlink to `ansible-inv` and that each environment has its own `.ansible` configuration directory with its own configuration and history file.

Then you could use something like this in your `ansible.cfg`:

```
inventory = /path/to/my/inventories/${AI_ENV}/hosts
```

So you could call ansible this way:

```
AI_ENV=development ansible -m ping all
```


# BETA STATUS
This software is in beta status. Please use with caution.
