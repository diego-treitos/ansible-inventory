# vim: set ts=2 sw=2 sts=2 et:

from setuptools import setup

VERSION='0.1.2'

setup(
    name = 'ansible-inventory',
    version = VERSION,
    description = 'Script to manage your Ansible Inventory and also can be used by ansible as a dynamic inventory source',
    license = 'GPLv3',
    platforms = ['linux'],
    author = 'Diego Blanco',
    author_email = 'diego.blanco@treitos.com',
    url = 'https://github.com/diego-treitos/ansible-inventory',
    download_url = 'https://github.com/diego-treitos/ansible-inventory/archive/v'+VERSION+'.tar.gz',
    keywords = ['ansible', 'inventory', 'dynamic', 'management'],
    scripts = ['ansible-inventory'],
    install_requires=['redis']
)
