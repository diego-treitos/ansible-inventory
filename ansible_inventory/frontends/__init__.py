# -*- coding:utf-8 -*-
# vim: set ts=2 sw=2 sts=2 et:

import cmd
import json
import readline
import signal
import subprocess
import sys
from ansible_inventory.lib import AnsibleInventory_Color, AnsibleInventory_Exception, AnsibleInventory_WarnException, AnsibleInventory_InfoException
from ansible_inventory.globals import VERSION, AUTHOR_NAME, AUTHOR_MAIL, URL


class AI_Console_ValidationError(Exception):
  pass


class AnsibleInventory_Console(cmd.Cmd):

  def console_handler( f ):
    def wrapper(self, arg ):
      # parse args
      args={ 0: f.__name__.split('do_')[1] }
      i=0
      for a in arg.split():
        i+=1
        if i>0 and '=' in a:
          args[i] = tuple(a.split('=', 1))
        else:
          args[i] = a

      # handle exceptions
      try:
        return f(self, args)
      except AnsibleInventory_Exception as e:
        targets = tuple( self.C(x) for x in e.targets )
        self.__error( e.__str__() % targets )
      except AnsibleInventory_WarnException as e:
        targets = tuple( self.C(x) for x in e.targets )
        self.__warn( e.__str__() % targets )
      except AnsibleInventory_InfoException as e:
        targets = tuple( self.C(x) for x in e.targets )
        self.__info( e.__str__() % targets )
    wrapper.__doc__ = f.__doc__
    return wrapper

  def __init__(self, inventory, config):
    super(AnsibleInventory_Console, self).__init__()
    self.inventory = inventory
    signal.signal(signal.SIGINT, self.__signal_sigint)

    self.history_file = config.history_file

    self.color = AnsibleInventory_Color( config )
    self.C = self.color.color

    self.intro = """
    Welcome to %s.

     Author: %s %s
    Project: %s

    Type 'help' for help.""" % ( self.color.BASE+'Ansible Inventory ' + VERSION,
                                 self.color.RESET+AUTHOR_NAME, '<'+AUTHOR_MAIL+'>'+self.color.BASE,
                                 self.color.RESET+URL )

    if self.color.use_colors:
      # We use \001 and \002 to delimit non printable characters so the history completion is not messed up
      self.prompt = '\n\001'+self.color.BASE+"\002¬¬ \001"+self.color.RESET+'\002'
    else:
      self.prompt = '\n¬¬ '

    self.allowed_commands = ['add', 'show', 'edit', 'del', 'help', 'exit' ]

  def emptyline(self):
    "Override the default from cmd.Cmd that executes last command instead"
    pass

  def __signal_sigint(self, signal, frame):
    "Catch sigint and exit cleanly"
    print('')
    self.do_exit(None)
    sys.exit(0)

  def __validate_args(self, args):
    "Validates the commands and args sent to the shell"

    # Get number of arguments
    n_args = args.keys().__len__()

    # Create initial structure to clasify positional and optional arguments
    args_dict = {
      'positional': {},
      'optional': {}
    }

    pos_i=0
    for i in range( 0, n_args ):
      if isinstance(args[i], tuple):
        args_dict['optional'][ args[i][0] ] = args[i][1]
      else:
        args_dict['positional'][ pos_i ] = args[i]
        pos_i+=1

    # Main command
    cmd = args_dict['positional'][0]

    # Check number of arguments
    if cmd == 'show':
      if n_args < 2:
        raise AI_Console_ValidationError('Not enough arguments')
    else:
      if n_args < 3:
        raise AI_Console_ValidationError('Not enough arguments')

    # Get subcommand (l2cmd) and check it
    if args_dict['positional'].__len__() < 2:
        raise AI_Console_ValidationError('No subcommand provided')
    l2cmd = args_dict['positional'][1]
    if not isinstance(l2cmd, str) or l2cmd not in ('host', 'group', 'var'):
      if cmd == 'show' and l2cmd not in ('host', 'group', 'hosts', 'groups', 'tree'):
        raise AI_Console_ValidationError('Wrong subcommand: %s' % l2cmd)

    # Convert the 3rd positional argument in the "name" optional argument
    if args_dict['positional'].__len__() == 3 and cmd+l2cmd != 'addvar':
      args[2] = ('name', args_dict['positional'][2])
      return self.__validate_args( args )

    # Check the number of positional arguments
    if args_dict['positional'].__len__() > 3:
      raise AI_Console_ValidationError('Too many positional arguments')

    # Initialize the posible options per command+subcommand and the posible option combinations
    l2cmd_opts = []
    l2cmd_combs = []
    if cmd == 'add':
      if l2cmd == 'host':
        l2cmd_opts = ['name', 'host', 'to_groups']
        l2cmd_combs = [
          ['name'],
          ['name', 'host'],
          ['name', 'to_groups'],
        ]
      elif l2cmd == 'group':
        l2cmd_opts = ['name', 'to_groups']
        l2cmd_combs = [
          ['name'],
          ['name', 'to_groups']
        ]
      elif l2cmd == 'var':
        l2cmd_opts = [ args[2][0], 'to_hosts', 'to_groups']
        l2cmd_combs = [
          [ args[2][0], 'to_hosts'],
          [ args[2][0], 'to_groups']
        ]

    elif cmd == 'edit':
      if l2cmd == 'host':
        l2cmd_opts = ['name', 'new_name', 'new_host']
        l2cmd_combs = [
          ['name', 'new_name'],
          ['name', 'new_host']
        ]
      elif l2cmd == 'group':
        l2cmd_opts = ['name', 'new_name']
        l2cmd_combs = [
          ['name', 'new_name']
        ]
      elif l2cmd == 'var':
        l2cmd_opts = ['name', 'new_name', 'new_value', 'in_hosts', 'in_groups']
        l2cmd_combs = [
          ['name', 'new_name', 'in_hosts'],
          ['name', 'new_name', 'in_groups'],
          ['name', 'new_value', 'in_hosts'],
          ['name', 'new_value', 'in_groups']
        ]

    elif cmd == 'del':
      if l2cmd == 'host':
        l2cmd_opts = ['name', 'from_groups']
        l2cmd_combs = [
          ['name'],
          ['name', 'from_groups'],
        ]
      elif l2cmd == 'group':
        l2cmd_opts = ['name', 'from_groups']
        l2cmd_combs = [
          ['name'],
          ['name', 'from_groups']
        ]
      elif l2cmd == 'var':
        l2cmd_opts = ['name', 'from_hosts', 'from_groups']
        l2cmd_combs = [
          ['name', 'from_hosts'],
          ['name', 'from_groups']
        ]

    elif cmd == 'show':
      if l2cmd in ['host', 'hosts']:
        l2cmd_opts = ['name', 'in_groups', 'ANY']
        l2cmd_combs = [
          ['ANY'],
        ]
      elif l2cmd in ['group', 'groups']:
        l2cmd_opts = ['name', 'in_groups', 'ANY']
        l2cmd_combs = [
          ['ANY'],
        ]
      elif l2cmd in ['tree']:
        l2cmd_opts = ['name']
        l2cmd_combs = [
          ['name']
        ]

    else:
      raise AI_Console_ValidationError('Wrong command: %s' % cmd)

    if not l2cmd_opts and not l2cmd_combs:
      raise AI_Console_ValidationError('Wrong subcommand %s' % l2cmd)

    # Check optional arguments
    if 'ANY' not in l2cmd_opts:
      for a in args_dict['optional']:
        if a not in l2cmd_opts:
          raise AI_Console_ValidationError('Invalid argument %s' % a)
    valid=False
    pos_args = list(args_dict['optional'].keys())
    pos_args.sort()
    for c in l2cmd_combs:
      c.sort()
      if pos_args == c or 'ANY' in c:
        valid=True
    if not valid:
      raise AI_Console_ValidationError('Invalid arguments')

    # Return the args_dict with the optional and positional arguments
    return args_dict

  def precmd(self, line):
    if line == 'EOF':
      print('')
      self.do_exit(None)
      sys.exit(0)
    if line and line.split() and line.split()[0] not in self.allowed_commands:
      self.__error('Invalid command')
      return ''
    return line

  def __ok(self, msg):
    if self.color.use_colors:
      print(self.color.BASE+"v   "+self.color.GOOD+'ok '+self.color.BASE+msg+self.color.RESET)
    else:
      print("v   ok "+msg)
    print('')

  def __info(self, msg):
    if self.color.use_colors:
      print(self.color.BASE+"-   "+self.color.INFO+'info '+self.color.BASE+msg+self.color.RESET)
    else:
      print("-   info "+msg)
    print('')

  def __warn(self, msg):
    if self.color.use_colors:
      print(self.color.BASE+"~   "+self.color.WARN+'warning '+self.color.BASE+msg+self.color.RESET)
    else:
      print("~   warning "+msg)
    print('')

  def __error(self, msg):
    if self.color.use_colors:
      print(self.color.BASE+"^   "+self.color.FAIL+'error '+self.color.BASE+msg+self.color.RESET)
    else:
      print("^   error "+msg)
    print('')

  def __confirm(self, msg):
    if self.color.use_colors:
      print(self.color.BASE+"·   "+self.color.INFO+'confirm '+self.color.BASE+msg+' [N/y]: '+self.color.RESET, end='')
    else:
      print("·   confirm "+msg+' [N/y]: ', end='')
    sys.stdout.flush()
    answer = sys.stdin.readline()
    if answer.lower().strip( '\n' ) in ('y', 'yes'):
      return True
    return False

  def do_exit(self, arg):
    'Exists Ansible Inventory console'
    readline.write_history_file( self.history_file )
    self.__info('Deica logo!')
    return True

  def __print_group_tree(self, group, level=0, preline='', last_node=False):
      hosts = self.inventory.get_group_hosts( group )
      hosts.sort()
      if hosts:
        last_host = hosts[-1]
      child = self.inventory.get_group_children( group )
      child.sort()
      if child:
        last_child = child[-1]

      if hosts or child:
        g_fork = '┬'
      else:
        g_fork = '─'

      if last_node:
        g_link = '╰'
      else:
        g_link = '├'

      if level == 0:
        print('     ╭─'+'─'*group.__len__()+'─╮')
        print(' ╭───┤ %s │' % self.C( group ))
        print(' │   ╰─'+'─'*group.__len__()+'─╯')
      else:
        print( preline +'\b\b │' )
        if last_node:
          print( preline +'\b\b │', end='' )
        else:
          print( preline, end='' )
        print('     ╭─%s─╮' % ('─'*group.__len__()) )
        print( preline, end='' )
        print('\b\b %s' % g_link, end='')
        print('─%s───╯ %s ╵' % (g_fork, self.C( group )) )

      for h in hosts:
        print( preline, end='')
        if h == last_host and not child:
          print(' ╰', end='' )
        else:
          print(' ├', end='' )
        print('╴%s' % self.C( h ))

      for g in child:
        if last_child == g:
          prel = preline + '  '
        else:
          prel = preline + ' │'
        self.__print_group_tree( g, level+1, preline=prel, last_node=last_child==g)

  def __print_vars( self, e_vars, pre_middle_var, pre_last_var ):
    e_line = ''
    e_vars_keys = []
    for v in e_vars:
      e_vars_keys.append( v )

    if e_vars_keys:
      e_vars_keys.sort()
      last_key = e_vars_keys[-1]
      longest_key = self.C(e_vars_keys[0]).__len__()
      for v in e_vars_keys:
        if self.C(v).__len__() > longest_key:
          longest_key = self.C(v).__len__()

      for v in e_vars_keys:
        if v == last_key:
          e_line+= pre_last_var
        else:
          e_line+= pre_middle_var

        var_line = '╴%%-%ds = %%s\n' % longest_key

        if isinstance( e_vars[v], dict ):
          if self.color.use_colors:
            from pygments import highlight, lexers, formatters
            var_dict = highlight(json.dumps(e_vars[v], sort_keys=True, indent=2),
                                      lexers.JsonLexer(),
                                      formatters.Terminal256Formatter(style='vim'))
            var_dict = var_dict.replace("\n", "\n  │       │ ")
          else:
            var_dict = json.dumps(e_vars[v], sort_keys=True, indent=2).replace("\n", "\n  │       │ ")
          e_line+= var_line % (self.C(v), var_dict)
        else:
          e_line+= var_line % (self.C(v), e_vars[v])

    return e_line

  def __print_list( self, e_list, start, newline ):
    try:
      rows, columns = subprocess.check_output(['stty', 'size']).split()
      rows = int(rows)
      columns = int(columns)
    except:
      rows, columns = 25, 80
    lines=start
    line_cols=start.__len__()

    for e in e_list:
      e_cols = e.__len__()
      if line_cols+e_cols+1 > columns:
        lines += newline + self.C(e)
        line_cols = newline.__len__() + e_cols
      else:
        lines += ' ' + self.C(e)
        line_cols+= 1 + e_cols
    return lines

  def __print_host( self, host, max_len ):
    host_line = '\n'
    host_line+= '             ╭─%s─╮\n' % ('─'*host.__len__())
    host_line+= '  ╭──────────┤ %s │\n' % self.C(host)
    host_line+= '  ├─╴vars╶╮  ╰─%s─╯\n' % ('─'*host.__len__())

    self.inventory.next_from_cache()
    h_vars =  self.inventory.get_host_vars( host )

    host_line+= self.__print_vars( h_vars, '  │       ├', '  │       ╰' )

    host_line+= '  │\n'

    self.inventory.next_from_cache()
    groups = self.inventory.get_host_groups( host )
    groups.sort()
    host_line+= self.__print_list( groups, '  ╰─╴groups╶(', '\n  │   ' )
    host_line+= ' )'
    print(host_line)

  def __print_group( self, group, max_len ):
    group_line = '\n'
    group_line+= '             ╭╌%s╌╮\n' % ('╌'*group.__len__())
    group_line+= '  ╭╌╌╌╌╌╌╌╌╌╌┤ %s ┆\n' % self.C(group)
    group_line+= '  ├╶╴vars╶╮  ╰╌%s╌╯\n' % ('╌'*group.__len__())

    self.inventory.next_from_cache()
    g_vars =  self.inventory.get_group_vars( group )

    vars_line = self.__print_vars( g_vars, '  ┆       ├', '  ┆       ╰' )

    if vars_line:
      group_line+=vars_line
    else:
      group_line = group_line.replace( 'vars╶╮', 'vars  ' )
    group_line+= '  ┆\n'

    self.inventory.next_from_cache()
    hosts = self.inventory.get_group_hosts( group )
    hosts.sort()
    group_line+= self.__print_list( hosts, '  ├╴╴hosts╶(', '\n  ┆   ' )
    group_line+= ' )\n'
    group_line+= '  ┆\n'

    self.inventory.next_from_cache()
    child = self.inventory.get_group_children( group )
    child.sort()
    group_line+= self.__print_list( child, '  ╰╴╴child╶[', '\n      ' )
    group_line+= ' ]'
    print( group_line )

  def __show_hosts( self, hosts, args_opt ):
    'Handle "show hosts" command'

    #( in_groups
    in_groups = []
    if 'in_groups' in args_opt:
      for g_regex in args_opt['in_groups'].split(','):
        self.inventory.next_from_cache()
        in_groups += self.inventory.list_groups( g_regex )

      filtered_hosts = []
      for h in hosts:
        remove_host = False
        self.inventory.next_from_cache()
        h_groups = self.inventory.get_host_groups( h )
        for g in in_groups:
          if g not in h_groups:
            remove_host = True
        if not remove_host:
          filtered_hosts.append(h)

      hosts = filtered_hosts
    #) in_groups

    #( vars filter
    filtered_hosts = []
    for h in hosts:
      remove_host = False
      for v in args_opt:
        if v not in ('in_groups', 'name'):
          self.inventory.next_from_cache()
          if not self.inventory.assert_host_var( h, v, args_opt[v] ):
            remove_host = True
      if not remove_host:
        filtered_hosts.append( h )
    hosts = filtered_hosts
    #)

    if not hosts:
      self.__warn('No host matched')
      return False

    max_len=0
    for n in hosts:
      cn = self.C(n)
      if cn.__len__() > max_len:
        max_len = cn.__len__()
    hosts.sort()

    self.__info('Here is your hosts list')
    for host in hosts:
      self.__print_host( host, max_len )

  def __show_groups( self, groups, args_opt ):
    'Handle "show groups" command'

    #( vars filter
    filtered_groups = []
    for g in groups:
      remove_group = False
      for v in args_opt:
        if v != 'name':
          self.inventory.next_from_cache()
          if not self.inventory.assert_group_var( g, v, args_opt[v] ):
            remove_group = True
      if not remove_group:
        filtered_groups.append( g )
    groups = filtered_groups
    #)

    if not groups:
      self.__warn('No group matched')
      return False

    max_len=0
    for n in groups:
      cn = self.C(n)
      if cn.__len__() > max_len:
        max_len = cn.__len__()
    groups.sort()

    self.__info('Here is your groups list')
    for group in groups:
      self.__print_group( group, max_len )

  @console_handler
  def do_show(self, args):
    """
    show host(s) [[name=]HOST_REGEX] [in_groups=GROUP_REGEX_LIST] [VAR_NAME=VAR_VALUE] [VAR_NAME=VAR_VALUE] ...
    show group(s) [[name=]GROUPS_REGEX] [VAR_NAME=VAR_VALUE] [VAR_NAME=VAR_VALUE] ...
    show tree <[name=]GROUP>

    HOST: Domain name or IP of the host
    VAR_NAME: Variable name
    VAR_VALUE: Variable value
    {SOMETHING}_REGEX: Regular expression (i.e.: name=test_.* )
    {SOMETHING}_REGEX_LIST: Comma separated list of regular expressions (i.e.: in_groups=test[1-3],example.*)
    """
    try:
      args = self.__validate_args( args )
    except AI_Console_ValidationError as e:
      self.__error( e.__str__() )
      self.do_help('show')
      return False

    args_opt = args['optional']
    args_pos = args['positional']

    name = None
    if 'name' in args_opt:
      name = args_opt['name']

    # SHOW HOST
    if args_pos[1] in ['host', 'hosts']:
      if name:
        hosts = self.inventory.list_hosts( name )
      else:
        hosts = self.inventory.list_hosts()
      return self.__show_hosts( hosts, args_opt )

    # SHOW GROUP
    if args_pos[1] in ['group', 'groups']:
      if name:
        groups = self.inventory.list_groups(name)
      else:
        groups = self.inventory.list_groups()
      return self.__show_groups( groups, args_opt )

    # SHOW TREE
    if args_pos[1] == 'tree':
      if name not in self.inventory.list_groups(name):
        self.__warn('No group matched')
        return False
      self.__info('Here is the group tree for %s' % self.C( name ))
      self.__print_group_tree( name )

  def __add_host( self, args_opt, to_groups ):
    'Handle "add host"'

    name = args_opt['name']
    host = None
    port = None

    if 'host' in args_opt:
      if ':' in args_opt['host']:
        host, port = args_opt['host'].split(':')
      else:
        host = args_opt['host']

    if not to_groups:
      self.inventory.add_host( name, host, port )
      self.__ok('Host %s added' % self.C(name))
    else:
      self.inventory.add_hosts_to_groups( name, to_groups )
      self.__ok('Host %s added to groups' % self.C(name))
    return True

  def __add_group( self, args_opt, to_groups ):
    'Handle "add group"'

    group = args_opt['name']

    if to_groups:
      for g_regex in to_groups:
        self.inventory.add_group_to_groups( group, g_regex )
      self.__ok('Group %s added to groups' % self.C(group))
    else:
      self.inventory.add_group( group )
      self.__ok('Group %s added' % self.C(group))
    return True

  def __add_var( self, args_opt, to_groups, to_hosts ):
    'Handle "add var"'

    for v in args_opt:
      if v not in ['to_hosts', 'to_groups']:
        v_name = v
        v_value = args_opt[v]

    if to_groups:
      for g_regex in to_groups:
        self.inventory.add_var_to_groups( v_name, v_value, g_regex )
      self.__ok('Var %s added to groups with value %s' % ( self.C(v_name), self.C(v_value) ) )

    if to_hosts:
      for h_regex in to_hosts:
        self.inventory.add_var_to_hosts( v_name, v_value, h_regex )
      self.__ok('Var %s added to hosts with value %s' % ( self.C(v_name), self.C(v_value) ) )
    return True

  @console_handler
  def do_add(self, args):
    """
    add host  <[name=]HOST> [host=<host>[:<host_port>]]
    add host  <[name=]HOST_REGEX> <to_groups=GROUP_REGEX_LIST>
    add group <[name=]GROUP> [to_groups=GROUP_REGEX_LIST]
    add var   <VAR_NAME=VAR_VALUE> <to_hosts=HOST_REGEX_LIST>
    add var   <VAR_NAME=VAR_VALUE> <to_groups=GROUP_REGEX_LIST>

    HOST: Domain name or IP of the host
    VAR_NAME: Variable name
    VAR_VALUE: Variable value
    {SOMETHING}_REGEX: Regular expression (i.e.: name=test_.* )
    {SOMETHING}_REGEX_LIST: Comma separated list of regular expressions (i.e.: in_groups=test[1-3],example.*)
    """
    try:
      args = self.__validate_args( args )
    except AI_Console_ValidationError as e:
      self.__error( e.__str__() )
      self.do_help('add')
      return False

    args_opt = args['optional']
    args_pos = args['positional']

    # to_groups used in host and group
    if 'to_groups' in args_opt:
      to_groups = args_opt['to_groups'].split(',')
    else:
      to_groups = []

    # to_hosts used in var
    if 'to_hosts' in args_opt:
      to_hosts = args_opt['to_hosts'].split(',')
    else:
      to_hosts = []

    # ADD HOST
    if args_pos[1] == 'host':
      return self.__add_host( args_opt, to_groups )

    # ADD GROUP
    elif args_pos[1] == 'group':
      return self.__add_group( args_opt, to_groups )

    # ADD VAR
    elif args_pos[1] == 'var':
      return self.__add_var( args_opt, to_groups, to_hosts )

  def __edit_host( self, args_opt ):
    'Handle "edit host"'

    name = args_opt['name']

    if 'new_name' in args_opt:
      msg = self.inventory.rename_host( name, args_opt['new_name'] )
      if msg:
        self.__warn(msg)
      else:
        self.__ok('Host %s renamed to %s' % ( self.C(name), self.C(args_opt['new_name'])))

    if 'new_host' in args_opt:
      if ':' in args_opt['new_host']:
        host, port = args_opt['new_host'].split(':')
      else:
        host = args_opt['new_host']
        port = None

      self.inventory.change_host( name, host, port )
      self.__ok('Host address for %s changed to %s' % ( self.C(name), self.C(args_opt['new_host'])))

    return True

  def __edit_group( self, args_opt ):
    'Handle "edit group"'

    g = args_opt['name']
    msg = self.inventory.rename_group( g, args_opt['new_name'] )
    if msg:
      self.__info(msg)
    else:
      self.__ok('Group %s renamed to %s' % (g, args_opt['new_name']))
    return True

  def __edit_var( self, args_opt ):
    'Handle "edit var"'

    v_name = args_opt['name']
    new_name = None
    new_value = None
    if 'new_name' in args_opt:
      new_name = args_opt['new_name']
    if 'new_value' in args_opt:
      new_value = args_opt['new_value']

    if 'in_groups' in args_opt:
      in_groups = args_opt['in_groups'].split(',')
    else:
      in_groups = []

    if in_groups:
      if new_name:
        for g_regex in in_groups:
          self.inventory.rename_group_var(v_name, new_name, g_regex)
        self.__ok('Variable %s renamed to %s in selected groups' % (self.C(v_name), self.C(new_name)))
      if new_value:
        for g_regex in in_groups:
          self.inventory.change_group_var(v_name, new_value, g_regex)
        self.__ok('Variable %s changed to %s in selected groups' % (self.C(v_name), self.C(new_value)))

    if 'in_hosts' in args_opt:
      in_hosts = args_opt['in_hosts'].split(',')
    else:
      in_hosts = []

    if in_hosts:
      if new_name:
        for h_regex in in_hosts:
          self.inventory.rename_host_var(v_name, new_name, h_regex)
        self.__ok('Variable %s renamed to %s in selected hosts' % (self.C(v_name), self.C(new_name)))
      if new_value:
        for h_regex in in_hosts:
          self.inventory.change_host_var(v_name, new_value, h_regex)
        self.__ok('Variable %s changed to %s in selected hosts' % (self.C(v_name), self.C(new_value)))

    return True

  @console_handler
  def do_edit(self, args):
    """
    edit host  <[name=]HOST> <new_name=NEW_NAME>
    edit host  <[name=]HOST> <new_host=NEW_HOST>
    edit group <[name=]GROUP> <new_name=NEW_NAME>
    edit var   <[name=]VAR_NAME> <new_name=NEW_NAME> <[in_hosts=HOST_REGEX_LIST | in_groups=GROUP_REGEX_LIST]>
    edit var   <[name=]VAR_NAME> <new_value=NEW_VALUE> <[in_hosts=HOST_REGEX_LIST | in_groups=GROUP_REGEX_LIST]>

    HOST: Domain name or IP of the host
    VAR_NAME: Variable name
    VAR_VALUE: Variable value
    {SOMETHING}_REGEX: Regular expression (i.e.: name=test_.* )
    {SOMETHING}_REGEX_LIST: Comma separated list of regular expressions (i.e.: in_groups=test[1-3],example.*)
    """
    try:
      args = self.__validate_args( args )
    except AI_Console_ValidationError as e:
      self.__error( e.__str__() )
      self.do_help('edit')
      return False

    args_opt = args['optional']
    args_pos = args['positional']

    # EDIT HOST
    if args_pos[1] == 'host':
      return self.__edit_host( args_opt )

    # EDIT GROUP
    if args_pos[1] == 'group':
      return self.__edit_group( args_opt )

    # EDIT VAR
    if args_pos[1] == 'var':
      return self.__edit_var( args_opt )

  def __del_host( self, h_regex, from_groups ):
    'Handle "del host"'

    hosts = self.inventory.list_hosts( h_regex )
    hosts.sort()
    c_hosts = []
    for h in hosts:
      c_hosts.append( self.C( h ) )
    if not from_groups:
      if not hosts:
        self.__warn('Host pattern %s does not match any host' % self.C(h_regex))
      elif self.__confirm('The following hosts will be permanently removed: %s.\n            Do you want to proceed?' % ', '.join( c_hosts ) ):
        for h in hosts:
          self.inventory.remove_host( h )
        self.__ok('The hosts have been removed')
      else:
        return False
    else:
      del_groups = []
      for g_regex in from_groups:
        gs = self.inventory.list_groups( g_regex )
        del_groups += gs

      self.__info('The hosts matching %s would be removed from the following groups:' % self.C(h_regex))
      for g in del_groups:
        print( ' '+self.C(g), end='')
      print('\n')
      if self.__confirm('Do you want to proceed?'):
        for h in hosts:
          self.inventory.remove_host( h_regex, from_groups=del_groups )
          self.__ok('Host %s removed from groups' % self.C(h))

    return True

  def __del_group( self, g_regex, from_groups ):
    'Handle "del group"'

    groups = self.inventory.list_groups( g_regex )
    groups.sort()

    if not from_groups:
      c_groups = []
      for g in groups:
        c_groups.append( self.C( g ) )
      if not groups:
        self.__warn('Group pattern %s does not match any group' % self.C(g_regex))
      elif self.__confirm('The following groups will be permanently removed: %s.\n            Do you want to proceed?' % ', '.join( c_groups ) ):
        some_error = False
        for g in groups:
          msg = self.inventory.remove_group( g )
          if msg:
            some_error = True
            self.__warn( msg )
        if not some_error:
          self.__ok('The groups have been removed')
      else:
        return False
    else:
      del_groups = []
      for g_rex in from_groups:
        gs = self.inventory.list_groups( g_rex )
        del_groups += gs

      self.__info('The groups matching %s would be removed from the following groups:' % self.C(g_regex))
      for g in del_groups:
        print( ' '+self.C(g), end='')
      print('\n')
      if self.__confirm('Do you want to proceed?'):
        for g in groups:
          self.inventory.remove_group( g, from_groups=del_groups )
          self.__ok('Group %s removed from groups' % self.C(g))

    return True

  def __del_var( self, var_name, from_groups, from_hosts ):
    'Handle "del var"'

    if from_groups:
      del_groups = []
      for g_regex in from_groups:
        gs = self.inventory.list_groups( g_regex )
        del_groups += gs
      self.__info('The variable %s would be removed from the following groups:' % self.C(var_name))
      for g in del_groups:
        print( ' '+self.C(g), end='')
      print('\n')
      if self.__confirm('Do you want to proceed?'):
        for g in del_groups:
          self.inventory.remove_group_var( var_name, g )
        self.__ok('Variable %s removed from groups' % self.C(var_name))
    elif from_hosts:
      del_hosts = []
      for h_regex in from_hosts:
        hs = self.inventory.list_hosts( h_regex )
        del_hosts += hs
      self.__info('The variable %s would be removed from the following hosts:' % self.C(var_name))
      for h in del_hosts:
        print( ' '+self.C(h), end='')
      print('\n')
      if self.__confirm('Do you want to proceed?'):
        for h in del_hosts:
          self.inventory.remove_host_var( var_name, h )
        self.__ok('Variable %s removed from hosts' % self.C(var_name))

    return True

  @console_handler
  def do_del(self, args):
    """
    del host  <[name=]HOST_REGEX> [from_groups=GROUP_REGEX_LIST]
    del group <[name=]GROUP_REGEX> [from_groups=GROUP_REGEX_LIST]
    del var   <[name=]VAR_NAME> <[from_hosts=HOST_REGEX_LIST | from_groups=GROUP_REGEX_LIST]>

    HOST: Domain name or IP of the host
    VAR_NAME: Variable name
    VAR_VALUE: Variable value
    {SOMETHING}_REGEX: Regular expression (i.e.: name=test_.* )
    {SOMETHING}_REGEX_LIST: Comma separated list of regular expressions (i.e.: in_groups=test[1-3],example.*)
    """
    try:
      args = self.__validate_args( args )
    except AI_Console_ValidationError as e:
      self.__error( e.__str__() )
      self.do_help('del')
      return False

    args_opt = args['optional']
    args_pos = args['positional']

    if 'from_groups' in args_opt:
      from_groups = args_opt['from_groups'].split(',')
    else:
      from_groups = []

    if 'from_hosts' in args_opt:
      from_hosts = args_opt['from_hosts'].split(',')
    else:
      from_hosts = []

    name = args_opt['name']

    # DEL HOST
    if args_pos[1] == 'host':
      return self.__del_host( name, from_groups )

    # DEL GROUP
    if args_pos[1] == 'group':
      return self.__del_group( name, from_groups )

    # DEL VAR
    if args_pos[1] == 'var':
      return self.__del_var( name, from_groups, from_hosts )

  def completedefault(self, text, line, begidx, endidx):
    current_line=line.split()
    cmd = current_line[ 0 ]
    cmd_map = {
      'add' : {
        'host' : { 'host': None, 'to_groups': None },
        'group': { 'to_groups': None },
        'var'  : { 'to_hosts': None, 'to_groups': None }
      },
      'del' : {
        'host' : { 'from_groups': None },
        'group': { 'from_groups': None },
        'var'  : { 'from_hosts': None, 'from_groups': None }
      },
      'edit': {
        'host' : { 'new_name': None, 'new_host': None },
        'group': { 'new_name': None },
        'var'  : {
          'new_name' : { 'in_hosts': None, 'in_groups': None },
          'new_value': { 'in_hosts': None, 'in_groups': None },
        }
      },
      'show': {
        'host': { 'in_groups': None },
        'hosts': { 'in_groups': None },
        'group': {},
        'groups': {},
        'tree': {}
      },
    }

    def __comp( _kind, _text ):
      self.inventory.next_from_cache()
      if _kind == 'host':
        return self.inventory.list_hosts( _text+'.*' )
      elif _kind == 'var':
        return self.inventory.list_vars( _text+'.*' )
      else:
        return self.inventory.list_groups( _text+'.*' )

    if cmd in cmd_map:
      if current_line.__len__() > 1:
        kind = current_line[ 1 ]
        if kind not in cmd_map[ cmd ].keys():
          for sc in cmd_map[ cmd ]:
            if sc.startswith( kind ):
              return [ sc+' ' ]
        else:
          options = list(cmd_map[ cmd ][ kind ].keys())

          if current_line.__len__() > 2:
            target = current_line[ 2 ]
          else:
            target = None

          if current_line.__len__() > 3:
            subtarget = current_line[ 3 ]
            options = list(cmd_map[ cmd ][ kind ].keys())
          else:
            subtarget = None

          if current_line.__len__() > 4 or (current_line.__len__() == 4 and not text):
            if cmd == 'edit' and kind == 'var' and subtarget.startswith('new_'):
              options = list(cmd_map[ cmd ][ kind ][ subtarget.split('=')[0] ].keys())
              if current_line.__len__() > 4:
                subtarget = current_line[ 4 ]
              else:
                subtarget = None

          if cmd == 'show':
            if kind in ('host', 'hosts'):
              if target is None or target in 'in_groups':
                return __comp( 'host', text ) + ['in_groups=']
              elif target.startswith('in_groups='):
                if subtarget is None and text != '':
                  subtarget = target
                else:
                  return __comp( 'var', text )
            if kind in ('group', 'groups'):
              if target and not text:
                return __comp( 'var', text )
              else:
                return __comp( 'group', text )

          if subtarget is not None:
            if 'groups=' in text or 'hosts=' in text:
              part = text.split('=')[1].split(',')[ -1 ]
              prepart = text.rpartition(',')[0]
              if prepart:
                prepart+=','
              else:
                prepart = text.split('=')[0]+'='
              if 'hosts=' in text:
                return [ prepart+x for x in __comp('host', part) ]
              return [ prepart+x for x in __comp('group', part) ]
            else:
              opt = []
              for o in [ op+'=' for op in options ]:
                if o.startswith( text ):
                  opt.append( o )
              return opt or options

          if target is not None:
            if text:
              return __comp( kind, text )
            return options
          return __comp( kind, text )
      else:
        return list(cmd_map[ cmd ].keys())
    return []
