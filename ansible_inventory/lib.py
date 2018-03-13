# -*- coding:utf-8 -*-
# vim: set ts=2 sw=2 sts=2 et:

import curses
import errno
import fcntl
import os
import time


# Exceptions
class AnsibleInventory_Exception( Exception ):

  def __init__(self, message, targets=()):
    super().__init__( message )
    if type( targets ) == str:
      self.targets = ( targets, )
    else:
      self.targets = tuple( targets )


class AnsibleInventory_WarnException( AnsibleInventory_Exception ):
  pass


class AnsibleInventory_InfoException( AnsibleInventory_Exception ):
  pass


# SimpleFlock from https://github.com/derpston/python-simpleflock
class SimpleFlock:
   """Provides the simplest possible interface to flock-based file locking. Intended for use with the `with` syntax. It will create/truncate/delete the lock file as necessary."""

   def __init__(self, path, timeout = None):
      self._path = path
      self._timeout = timeout
      self._fd = None

   def __enter__(self):
      self._fd = os.open(self._path, os.O_CREAT)
      start_lock_search = time.time()
      while True:
         try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Lock acquired!
            return
         except (OSError, IOError) as ex:
            if ex.errno != errno.EAGAIN:  # Resource temporarily unavailable
               raise
            elif self._timeout is not None and time.time() > (start_lock_search + self._timeout):
               # Exceeded the user-specified timeout.
               raise

         # TODO It would be nice to avoid an arbitrary sleep here, but spinning
         # without a delay is also undesirable.
         time.sleep(0.1)

   def __exit__(self, *args):
      fcntl.flock(self._fd, fcntl.LOCK_UN)
      os.close(self._fd)
      self._fd = None

      # Try to remove the lock file, but don't try too hard because it is
      # unnecessary. This is mostly to help the user see whether a lock
      # exists by examining the filesystem.
      try:
         os.unlink(self._path)
      except:
         pass


# Colors
class AnsibleInventory_Color:

  BASE = '\x1b[1;37m'
  FAIL = '\x1b[1;31m'
  GOOD = '\x1b[1;32m'
  WARN = '\x1b[1;33m'
  INFO = '\x1b[1;34m'
  RESET = '\x1b[0;0m'

  def __init__( self, config ):
    self.use_colors = config.use_colors
    self.colors = []

    if self.use_colors:
      curses.setupterm()
      if curses.tigetnum("colors") >= 256:
        self.colors = self.__generate_colors256()
      else:
        self.colors = self.__generate_colors()

  def __generate_colors( self ):
    color_list = []
    for style in range( 3 ):
      for fg in range(31, 38):
        color = ';'.join([str(style), str(fg)])
        color_list.append(color)
    return color_list

  def __generate_colors256( self ):
    dark_colors = list(range(0, 8))+list(range(16, 28))+list(range(52, 76))+list(range(232, 250))
    color_list = []
    for c_256_n in range( 1, 255 ):
      if c_256_n not in dark_colors:
        # Grant all colors have the same string length
        if c_256_n < 10:
          c_256_s = '00%d' % c_256_n
        elif c_256_n < 100:
          c_256_s = '0%d' % c_256_n
        else:
          c_256_s = '%d' % c_256_n
        color = '38;5;' + c_256_s
        color_list.append( color )
    return color_list

  def color( self, word, word_to_hash=None ):
    if not self.use_colors:
      return word
    if not word_to_hash:
      word_to_hash = word
    n=0
    for c in word_to_hash:
      n+=ord(c)
    n = n*word_to_hash.__len__()**2
    color = self.colors[ n % self.colors.__len__() ]
    return '\x1b[%sm%s\x1b[0m' % (color, word)
