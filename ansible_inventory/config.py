# -*- coding:utf-8 -*-
# vim: set ts=2 sw=2 sts=2 et:

import configparser
import os
import readline
from ansible_inventory.backends import AnsibleInventory_FileBackend, AnsibleInventory_RedisBackend
from ansible_inventory.lib import AnsibleInventory_Exception


# ( CONFIG
class AnsibleInventory_Config:

  default_config = """[global]
  use_colors = True

  # backend: redis, file
  backend = file


  [file_backend]
  path = ~/.ansible/inventory.json

  [redis_backend]
  host =
  port =
  password =
  inventory_name = ansible_inventory
  """

  available_backends = {
    'file': AnsibleInventory_FileBackend,
    'redis': AnsibleInventory_RedisBackend
  }

  def __init__( self, ai_exec_file ):
    # check if we are using a symlinked instance
    if os.path.islink( ai_exec_file ):
      # We do this here and not in __main__ so we keep
      # the same behaviour even if this is used as a module
      self.config_home = os.path.join( os.path.dirname( os.path.abspath( ai_exec_file ) ), '.ansible' )
    else:
      self.config_home = os.path.join( os.environ['HOME'], '.ansible' )

    # define basic options
    self.config_file = os.path.join( self.config_home, 'ansible-inventory.cfg' )
    self.history_file = os.path.join( self.config_home, 'ansible-inventory_history' )

    # check configuration requirements
    self.__check_requirements()

    # read configuration
    self.__config = configparser.ConfigParser()
    self.__config.read( self.config_file )

    # option declarations (for clarity)
    self.use_colors = True
    self.backend = {
      'class': AnsibleInventory_FileBackend,
      'parameters': {}
    }

    # Parse configuration
    self.use_colors = self.__config['global'].getboolean('use_colors')

    backend_id = self.__config['global']['backend'].lower()
    if backend_id in self.available_backends:
      self.backend['class'] = self.available_backends[backend_id]
      self.backend['parameters'] = self.__config[backend_id+'_backend']
    else:
      raise AnsibleInventory_Exception( "No valid backend found" )

  def __check_requirements( self ):
    if not os.path.exists( self.config_home ):
      os.mkdir( self.config_home )

    if not os.path.exists( self.config_file ):
      with open( self.config_file, 'w' ) as cf:
        cf.write( self.default_config )
        cf.close()

    if not os.path.exists( self.history_file ):
      open( self.history_file, 'a' ).close()
    readline.read_history_file( self.history_file )
    readline.set_completer_delims(' ')
# )
