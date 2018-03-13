# -*- coding:utf-8 -*-
# vim: set ts=2 sw=2 sts=2 et:

import json
import os
import time
import uuid
from ansible_inventory.lib import AnsibleInventory_Exception, SimpleFlock


class AnsibleInventory_Backend:

    def __init__( self, backend_parameters, config ):
      self.__lock = None

    def load_inventory( self ):
      raise AnsibleInventory_Exception( "backend.load_inventory: Not implemented" )

    def save_inventory( self ):
      raise AnsibleInventory_Exception( "backend.save_inventory: Not implemented" )

    def lock( self ):
      raise AnsibleInventory_Exception( "backend.lock: Not implemented" )

    def unlock( self ):
      raise AnsibleInventory_Exception( "backend.unlock: Not implemented" )


class AnsibleInventory_FileBackend( AnsibleInventory_Backend ):
  "Backend class for ansible-inventory that uses a json file for storage"

  def __init__( self, backend_parameters, config ):
    self.lockfile = '/tmp/.ansible-inventory_file_backend.lock'
    self.__lock = SimpleFlock('/tmp/.ansible-inventory_file_backend_main.lock',
                              timeout=3)

    self.json_path = os.path.expanduser(
      backend_parameters['path'].strip('"\'')
    )
    if not os.path.isabs( self.json_path ):
      self.json_path = os.path.join( config.config_home, self.json_path )

  def load_inventory(self):
    "Returns a dictionary with the inventory contents as required by Inventory class"
    if os.path.exists( self.json_path ):
      with SimpleFlock( self.lockfile, timeout=3 ):
        with open( self.json_path ) as inv_file:
          return json.loads( inv_file.read() )
    else:
        return {}

  def save_inventory(self, inventory):
    "Saves the inventory from a dictionary with the inventory contents from the Inventory class"
    with SimpleFlock( self.lockfile, timeout=3 ):
      with open( self.json_path, 'w' ) as inv_file:
        inv_file.write( json.dumps( inventory ) )

  def lock(self):
    "Locks the backend for reading and writting"
    self.__lock.__enter__()

  def unlock(self):
    "Unlocks the backend"
    self.__lock.__exit__()


class AnsibleInventory_RedisBackend( AnsibleInventory_Backend ):
  "Backend class for ansible-inventory that uses redis for storage"

  def __init__( self, backend_parameters, config ):
    import redis

    # Set default values
    host = backend_parameters['host']
    port = 6379
    inventory_name = 'ansible_inventory'
    password = None

    # Use configured parameters when available
    if 'port' in backend_parameters and backend_parameters['port']:
      port = int( backend_parameters['port'] )
    if 'password' in backend_parameters and backend_parameters['password']:
      password = backend_parameters['password']
    if 'inventory_name' in backend_parameters and backend_parameters['inventory_name']:
      inventory_name = backend_parameters['inventory_name']

    self.r = redis.Redis( host=host, port=port, password=password )
    self.i = inventory_name
    self.uuid = str( uuid.uuid4() )
    self.__lock_name = inventory_name + '_redis_backend_lock'
    self.__timeout = 3  # seconds

  def load_inventory( self ):
    "Returns a dictionary with the inventory contents as required by Inventory class"
    i = self.r.get( self.i )
    if i:
      return json.loads( i.decode("utf-8") )
    else:
      return {}

  def save_inventory(self, inventory):
    "Saves the inventory from a dictionary with the inventory contents from the Inventory class"
    self.r.set( self.i, json.dumps( inventory ) )

  def lock(self):
    "Locks the backend for reading and writting"
    # Try to get the lock or raise exception on timeout
    t=0
    while not self.r.set( self.__lock_name, self.uuid, nx=True, px=self.__timeout*1000 ):
      if t >= self.__timeout:
        raise BlockingIOError
      time.sleep( 0.5 )
      t+=0.5

  def unlock(self):
    "Unlocks the backend"
    if self.r.get( self.__lock_name ) == self.uuid:
      self.r.delete( self.__lock_name )
