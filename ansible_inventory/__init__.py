# -*- coding:utf-8 -*-
# vim: set ts=2 sw=2 sts=2 et:

import ast
import json
from re import fullmatch
from ansible_inventory.lib import AnsibleInventory_Exception


class AnsibleInventory:

  # Inventory variable
  __I = None

### Internal inventory format
#{
#          "all"   : { 'hosts':[ all hosts here ], 'children':[], 'vars',{} },
#    "databases"   : {
#            "hosts" : [ "host1.example.com", "host2.example.com" ],
#            "vars"  : {
#                  "a" : true
#            }
#    },
#    "webservers"  : [ "host2.example.com", "host3.example.com" ],
#    "atlanta"     : {
#          "hosts"   : [ "host1.example.com", "host4.example.com", "host5.example.com" ],
#          "vars"    : {
#                "b"   : false
#          },
#          "children": [ "marietta", "5points" ]
#    },
#    "marietta"    : [ "host6.example.com" ],
#    "5points"     : [ "host7.example.com" ]
#       "_meta"    : {
#         "hostvars" : {
#           "moocow.example.com"     : { "asdf" : 1234 },
#           "llama.example.com"      : { "asdf" : 5678 },
#           "xeira"                  : { "ansible_host" : xeira.example.com },
#         }
#    }
#}

  def write(f):
    "Decorator for functions that change the inventory. This should grant inventory integrity when several concurrent ansible-inventory sessions"
    def wrapper(self, *args, **kwargs):
      try:
        self.backend.lock()
        self.reload()
        r = f(self, *args, **kwargs)
        self.save()
        return r
      except BlockingIOError:
        raise AnsibleInventory_Exception("Backend temporally unavailable. Please try again.")
      except AnsibleInventory_Exception:
        raise
      finally:
        self.backend.unlock()

    return wrapper

  def read(f):
    "Decorator for functions that read, so they use they have the most updated information in case of several concurrent ansible-inventory sessions"
    def wrapper(self, *kargs, **kwargs):
      try:
        if self.__from_cache:
          self.__from_cache = False
          self.reload()
        return f(self, *kargs, **kwargs)
      except Exception as e:
        raise AnsibleInventory_Exception( e.__str__() )
    return wrapper

  def __init__(self, backend):
    self.backend = backend
    self.reload()
    self.__from_cache = False

  def next_from_cache( self ):
    'This function can be called before calling any "read" method so it does not refresh the inventory from the backend'
    self.__from_cache = True

  def __ensure_inventory_skel(self):
    'Ensures the basic structure of the inventory is pressent'
    if '_meta' not in self.__I:
      self.__I['_meta'] = {}
    if 'all' not in self.__I:
      self.__I['all'] = {
        'children': [],
        'hosts': [],
        'vars': {}
      }
    if 'hostvars' not in self.__I['_meta']:
      self.__I['_meta']['hostvars'] = {}

  def save(self):
    "Saves the inventory to persistence backend"
    self.backend.save_inventory( self.__I )

  def reload(self):
    "Loads the inventory from the persistence backend"
    self.__I = self.backend.load_inventory()
    self.__ensure_inventory_skel()

  def __get_group_hosts(self, group):
    'Internal: Returns a list of hosts in a group'
    if group in self.__I:
      if isinstance( self.__I[group], list):
        return self.__I[group]
      if isinstance( self.__I[group], dict ):
        return self.__I[group]['hosts']
    else:
      return []

  def __get_host_groups(self, host):
    'Internal: Returns a list of groups where a host belongs'
    groups = []
    for g in self.__I:
      if g == '_meta':
        continue
      if host in self.__get_group_hosts(g):
        groups.append(g)
    return groups

  def __get_group_children(self, group):
    'Internal: Returns the list of subgroups in a group'
    if group in self.__I:
      if isinstance( self.__I[group], dict ) and 'children' in self.__I[group]:
        return self.__I[group]['children']
    return []

  def __set_host_host(self, h_name, host):
    'Sets or replaces a host address for a host'
    if h_name in self.__I['_meta']['hostvars']:
      self.__I['_meta']['hostvars'][h_name]['ansible_host'] = host
    else:
      self.__I['_meta']['hostvars'][h_name] = { 'ansible_host': host }

  def __set_host_port(self, h_name, port):
    'Sets or replaces a host address for a host'
    if h_name in self.__I['_meta']['hostvars']:
      self.__I['_meta']['hostvars'][h_name]['ansible_port'] = port
    else:
      self.__I['_meta']['hostvars'][h_name] = { 'ansible_port': port }

  def __parse_var( self, raw_value ):
    'Parses a var and returns a string, a list or a dict'
    try:
      v_value = ast.literal_eval( raw_value )
    except Exception:
      v_value = raw_value
    return v_value

  @read
  def get_ansible_json(self):
    'Returns the ansible json'
    return json.dumps( self.__I )

  @read
  def get_ansible_host_json(self, host):
    'Returns the ansible json for a host'
    if host in self.__I['_meta']['hostvars']:
      return json.dumps( self.__I['_meta']['hostvars'][ host ] )
    return json.dumps( {} )

  @read
  def list_hosts(self, h_regex='.*'):
    'Returns a list of known hosts in the inventory. If regex specified only matching hosts will be returned'
    hosts = []
    for g in self.__I:
      if g == '_meta':
        for h in self.__I['_meta']['hostvars']:
          if h not in hosts and fullmatch( h_regex, h ):
            hosts.append( h )
      else:
        for h in self.__get_group_hosts( g ):
          if h not in hosts and fullmatch( h_regex, h ):
            hosts.append( h )
    return hosts

  @read
  def list_groups(self, g_regex='.*'):
    'Returns a list of available groups. If g_regex is specified, only matching groups will be returned'
    groups = []
    for g in self.__I:
      if g == '_meta':
        continue
      if fullmatch( g_regex, g ):
        groups.append(g)
    return groups

  @read
  def list_vars( self, v_regex='.*' ):
    'Returns a list of variables in the inventory. If regex specified only matching variables will be returned.'
    i_vars = []
    for g in self.__I:
      if g == '_meta':
        for h in self.__I['_meta']['hostvars']:
          for v in self.__I['_meta']['hostvars'][ h ]:
            if v not in i_vars and fullmatch( v_regex, v ):
              i_vars.append( v )
      else:
        for v in self.__I[ g ]['vars']:
          if v not in i_vars and fullmatch( v_regex, v ):
            i_vars.append( v )
    return i_vars

  @read
  def get_group_vars(self, group):
    'Returns a dict with the group vars'
    if group in self.__I:
      if isinstance( self.__I[group], dict):
        if 'vars' in self.__I[group]:
          return self.__I[group]['vars']
    return {}

  @read
  def get_group_hosts(self, group):
    'Returns a list of hosts in a group'
    return self.__get_group_hosts( group )

  @read
  def get_group_children(self, group):
    'Returns the list of subgroups in a group'
    return self.__get_group_children( group )

  @read
  def get_group_parents(self, group):
    'Returns a list of the group parents of group'
    g_parents = []
    for g in self.__I:
      if isinstance( self.__I[g], dict ) and 'children' in self.__I[g] and group in self.__I[g]['children']:
        g_parents.append(g)
    return g_parents

  @read
  def get_host_vars(self, host):
    'Returns a dict with the host vars'
    if host in self.__I['_meta']['hostvars']:
      return self.__I['_meta']['hostvars'][host]
    else:
      return {}

  @read
  def get_host_groups(self, host):
    'Returns a list of groups where a host belongs'
    return self.__get_host_groups( host )

  @read
  def assert_host_var(self, host, v_name, v_value_regex ):
    'Checks if a host has a variable with v_name with a matching value of v_value_regex'
    self.next_from_cache()
    h_vars = self.get_host_vars( host )
    if v_name in h_vars and fullmatch( v_value_regex, str(h_vars[v_name]) ):
      return True
    return False

  @read
  def assert_group_var(self, group, v_name, v_value_regex ):
    'Checks if a group has a variable with v_name with a matching value of v_value_regex'
    self.next_from_cache()
    g_vars = self.get_group_vars( group )
    if v_name in g_vars and fullmatch( v_value_regex, str(g_vars[v_name]) ):
      return True
    return False

  @write
  def add_hosts_to_groups(self, h_regex, g_regex_list):
    'Adds a hosts matching h_regex to groups matching g_regex from a list'
    self.next_from_cache()
    matching_hosts = self.list_hosts( h_regex )
    if not matching_hosts:
      raise AnsibleInventory_Exception('No host matches your selection')

    matching_groups = []
    for g_regex in g_regex_list:
      self.next_from_cache()
      m_groups = self.list_groups( g_regex )
      if not m_groups:
        raise AnsibleInventory_Exception("No group matches '%s'" % g_regex)
      matching_groups += m_groups

    for h_name in matching_hosts:
      for g_name in matching_groups:
        if isinstance( self.__I[ g_name ], list ):
          if h_name not in self.__I[ g_name ]:
            self.__I[ g_name ].append( h_name )
        elif isinstance( self.__I[ g_name ], dict ):
          if h_name not in self.__I[ g_name ]['hosts']:
            self.__I[ g_name ]['hosts'].append( h_name )

  @write
  def add_host(self, h_name, h_host=None, h_port=None ):
    'Adds a host'
    self.next_from_cache()
    if h_name in self.list_hosts():
      raise AnsibleInventory_Exception('Host %s already exists', h_name)
    else:
      self.__I['all']['hosts'].append( h_name )
      self.__I['_meta']['hostvars'][ h_name ] = {}

    if h_host:
      self.__set_host_host( h_name, h_host )
    if h_port:
      self.__set_host_port( h_name, h_port )

  @write
  def add_group(self, group):
    'Adds a group'
    if group not in self.__I:
      self.__I[ group ] = {
        'hosts': [],
        'vars': {},
        'children': []
      }
    else:
      raise AnsibleInventory_Exception('Group %s already exists', group)

  @write
  def add_group_to_groups(self, group, g_regex):
    'Adds a single group to groups matching g_regex'
    self.next_from_cache()
    if group not in self.list_groups():
      raise AnsibleInventory_Exception('Group %s does not exist', targets=group)

    self.next_from_cache()
    matching_groups = self.list_groups( g_regex )
    if not matching_groups:
      raise AnsibleInventory_Exception('No group matches your selection')

    for g in matching_groups:
      if isinstance( self.__I[g], list):
        hosts = self.__I[g]
        self.__I[g] = {
          'hosts': hosts,
          'vars': {},
          'children': []
        }
      elif isinstance( self.__I[g], dict) and 'children' not in self.__I[g]:
        self.__I[g]['children'] = []

      if group not in self.__I[g]['children']:
        self.__I[g]['children'].append( group )

  @write
  def edit_host_vars(self, h_name, callback):
    'Edits host vars by calling "callback( vars_dict )". It locks the inventory until callback returns with a new "vars_dict" with the new vars.'
    self.next_from_cache()
    hosts = self.list_hosts()
    if h_name not in hosts:
      raise AnsibleInventory_Exception('Host %s does not exist', h_name)

    if h_name in self.__I['_meta']['hostvars']:
      h_vars = self.__I['_meta']['hostvars'][h_name]
    else:
      h_vars = {}

    new_vars = callback( h_vars )

    if new_vars and isinstance(new_vars, dict):
      self.__I['_meta']['hostvars'][h_name] = new_vars

  @write
  def edit_group_vars(self, g_name, callback):
    'Edits group vars by calling "callback( vars_dict )". It locks the inventory until callback returns with a new "vars_dict" with the new vars.'
    self.next_from_cache()
    groups = self.list_groups()
    if g_name not in groups:
      raise AnsibleInventory_Exception('Group %s does not exist', g_name)

    if isinstance( self.__I[g_name], list):
      hosts = self.__I[g_name]
      self.__I[g_name] = {
        'hosts': hosts,
        'vars': {},
        'children': []
      }
    elif isinstance( self.__I[g_name], dict) and 'vars' not in self.__I[g_name]:
      self.__I[g_name]['vars'] = {}

    g_vars = self.__I[g_name]['vars']

    new_vars = callback( g_vars )

    if new_vars and isinstance(new_vars, dict):
      self.__I[g_name]['vars'] = new_vars

  @write
  def add_var_to_groups(self, v_name, raw_value, g_regex):
    'Adds a variable a to groups matching g_regex'
    self.next_from_cache()
    matching_groups = self.list_groups( g_regex )
    if not matching_groups:
      raise AnsibleInventory_Exception('No group matches your selection')

    v_value = self.__parse_var( raw_value )
    exist_in = []
    for g in matching_groups:
      if isinstance( self.__I[g], list):
        hosts = self.__I[g]
        self.__I[g] = {
          'hosts': hosts,
          'vars': {},
          'children': []
        }
      elif isinstance( self.__I[g], dict) and 'vars' not in self.__I[g]:
        self.__I[g]['vars'] = {}

      if v_name not in self.__I[g]['vars']:
        self.__I[g]['vars'][v_name] = v_value
      else:
        exist_in.append( g )

    if exist_in:
      str_list = '%s ' * exist_in.__len__()
      raise AnsibleInventory_Exception('Var %s already exist in these groups: '+str_list, targets=(v_name,)+tuple( exist_in ) )

  @write
  def add_var_to_hosts(self, v_name, raw_value, h_regex):
    'Adds a variable to hosts matching h_regex'
    self.next_from_cache()
    matching_hosts = self.list_hosts( h_regex )
    if not matching_hosts:
      raise AnsibleInventory_Exception('No host matches your selection')

    v_value = self.__parse_var( raw_value )
    exist_in = []
    for h in matching_hosts:
      if h not in self.__I['_meta']['hostvars']:
        self.__I['_meta']['hostvars'][h] = {v_name : v_value}
      elif v_name not in self.__I['_meta']['hostvars'][h]:
        self.__I['_meta']['hostvars'][h][v_name] = v_value
      else:
        exist_in.append( h )
    if exist_in:
      str_list = '%s ' * exist_in.__len__()
      raise AnsibleInventory_Exception('Var %s already exist in these hosts: '+str_list, targets=(v_name,)+tuple( exist_in ) )

  @write
  def rename_host(self, h_name, new_name):
    'Renames a host'
    self.next_from_cache()
    hosts = self.list_hosts()
    if new_name in hosts:
      raise AnsibleInventory_Exception('Host %s already exists', new_name)
    if h_name not in hosts:
      raise AnsibleInventory_Exception('Host %s does not exist', h_name)

    if h_name in self.__I['_meta']['hostvars']:
      hvars = self.__I['_meta']['hostvars'].pop(h_name)
      self.__I['_meta']['hostvars'][new_name] = hvars
    for g in self.__get_host_groups( h_name ):
      if isinstance( self.__I[g], list ):
        self.__I[g].remove( h_name )
        self.__I[g].append( new_name )
      elif isinstance( self.__I[g], dict):
        self.__I[g]['hosts'].remove( h_name )
        self.__I[g]['hosts'].append( new_name )

  @write
  def change_host(self, h_name, h_host=None, h_port=None):
    'Changes the host address or port of a host'
    self.next_from_cache()
    if h_name not in self.list_hosts():
      raise AnsibleInventory_Exception('Host %s does not exist', h_name)
    if h_host:
      self.__set_host_host( h_name, h_host )
    if h_port:
      self.__set_host_port( h_name, h_port )

  @write
  def rename_host_var(self, v_name, new_name, h_regex):
    'Renames a variable in a set of hosts matching a regular expression'
    self.next_from_cache()
    for h in self.list_hosts():
      if fullmatch( h_regex, h ) and h in self.__I['_meta']['hostvars'] and v_name in self.__I['_meta']['hostvars'][h]:
        v_value = self.__I['_meta']['hostvars'][h].pop(v_name)
        self.__I['_meta']['hostvars'][h][new_name] = v_value

  @write
  def change_host_var(self, v_name, raw_value, h_regex):
    'Changes the value of a variable in the hosts matching a regular expression in case it is defined'
    self.next_from_cache()
    for h in self.list_hosts():
      if fullmatch( h_regex, h ) and h in self.__I['_meta']['hostvars'] and v_name in self.__I['_meta']['hostvars'][h]:
        self.__I['_meta']['hostvars'][h][v_name] = self.__parse_var( raw_value )

  @write
  def rename_group(self, g_name, new_name):
    'Renames a group'
    if new_name in self.__I:
      raise AnsibleInventory_Exception('Group %s already exists', new_name)
    if g_name not in self.__I:
      raise AnsibleInventory_Exception('Group %s does not exist', g_name)
    g_data = self.__I.pop(g_name)
    self.__I[new_name] = g_data
    for g_parent in self.get_group_parents( g_name ):
      self.remove_group( g_name, from_groups=[g_parent] )
      self.add_group_to_groups( new_name, g_parent )

  @write
  def rename_group_var(self, v_name, new_name, g_regex):
    'Renames a variable in a set of groups matching a regular expression'
    for g in self.__I:
      if g == '_meta':
        continue
      if fullmatch( g_regex, g ) and isinstance( self.__I[g], dict) and 'vars' in self.__I[g]:
        if v_name in self.__I[g]['vars']:
          v_value = self.__I[g]['vars'].pop(v_name)
          self.__I[g]['vars'][new_name] = v_value

  @write
  def change_group_var(self, v_name, raw_value, g_regex):
    'Changes the value of a variable in the groups matching a regular expression in case it is defined'
    for g in self.__I:
      if g == '_meta':
        continue
      if fullmatch( g_regex, g ) and isinstance( self.__I[g], dict) and 'vars' in self.__I[g]:
        if v_name in self.__I[g]['vars']:
          self.__I[g]['vars'][v_name] = self.__parse_var( raw_value )

  @write
  def remove_host(self, h_name, from_groups=[]):
    'Removes the selected host. If from_groups is provided, the host will only removed from those groups.'
    if from_groups:
      groups = from_groups
    else:
      groups = self.__get_host_groups( h_name )
      if h_name in self.__I['_meta']['hostvars']:
        self.__I['_meta']['hostvars'].pop(h_name)
    for g in groups:
      g_hosts = self.__get_group_hosts( g )
      if g_hosts and h_name in g_hosts:
        g_hosts.remove( h_name )

  @write
  def remove_group(self, g_name, from_groups=[]):
    'Removes the selected group. If from_groups is provided, the group will only removed from those groups.'
    if from_groups:
      for g in from_groups:
        g_child = self.__get_group_children( g )
        if g_name in g_child:
          g_child.remove( g_name )
    else:
      if g_name == 'all':
        raise AnsibleInventory_Exception('Group %s cannot be removed', 'all')
      for g in self.__I:
        g_child = self.__get_group_children( g )
        if g_name in g_child:
          g_child.remove( g_name )
      if g_name in self.__I:
        self.__I.pop( g_name )
      else:
        raise AnsibleInventory_Exception('Group %s does not exist.', g_name)

  @write
  def remove_host_var(self, v_name, h_name ):
    'Removes a variable from a host'
    if h_name in self.__I['_meta']['hostvars'] and v_name in self.__I['_meta']['hostvars'][h_name]:
      self.__I['_meta']['hostvars'][h_name].pop( v_name )

  @write
  def remove_group_var(self, v_name, g_name):
    'Removes a variable from a group'
    if g_name in self.__I and 'vars' in self.__I[g_name] and v_name in self.__I[g_name]['vars']:
      self.__I[g_name]['vars'].pop( v_name )
