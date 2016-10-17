# ansible-inventory
Script to manage your Ansible Inventory and also can be used by ansible as a dynamic inventory source


![demo](http://i.imgur.com/xeSCYMc.gif)


## Introduction
The idea is to have a single script that allows you to manage your inventory hosts, groups and variables.

When you have to change a variable that is in several hosts or groups, or you need to change a host that is in several groups, etc., you need to edit several lines of a static file inventory, which is laborious and error prone. With `ansible-inventory` we try to fix these problems and ease the ansible inventory management.

## Installation
Ansible Inventory requires python3. In case you want to use the `redis` backend, you will also need to install [redis-py]( https://github.com/andymccurdy/redis-py ) (`sudo apt-get install python3-redis`).

You can then place the `ansible-inventory` script wherever you want inside your `PATH`.

The first time you execute the script, it will create the necesary directories and default configurations inside your user's `HOME`.

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
```

Currently you can choose between 2 backends:

 * **file_backend**: It uses a file to store the inventory in json format.
 * **redis_backend**: It uses redis to store the inventory in a variable in json format. Note that you will need to enable redis AOF to have persistence. More in the [redis persistence documentation]( http://redis.io/topics/persistence ).

Both backends support concurrency, although in the case of Redis, the concurrency is limited to a single master scenario for now.

You can configure `ansible-inventory` as the inventory in your `ansible.cfg` file so ansible will know about the inventory that you are handling through `ansible-inventory`. This way you wont have to run the commands with `ansible -i /path/to/ansible-inventory`. To do this, edit your ansible configuration file in `/etc/ansible/ansible.cfg` or `~/.ansible.cfg` and congiure your inventory like this:

```
[defaults]

inventory = /path/to/ansible-inventory

...
```


# ALPHA STATUS
This software is in an alpha status, there is still a lot of testing to do, documenting and bugfixing. Please do not use in a production environment
