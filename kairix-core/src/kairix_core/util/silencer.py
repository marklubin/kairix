

import os
import functools

def silent(func):
  """Decorator that silences all stdout/stderr output from a function."""
  @functools.wraps(func)
  def wrapper(*args, **kwargs):
      # Save current stdout/stderr
      old_stdout = os.dup(1)
      old_stderr = os.dup(2)

      try:
          # Open /dev/null
          devnull = os.open(os.devnull, os.O_WRONLY)

          # Redirect stdout/stderr to /dev/null
          os.dup2(devnull, 1)
          os.dup2(devnull, 2)

          # Close the devnull fd
          os.close(devnull)

          # Call the function
          result = func(*args, **kwargs)

      finally:
          # Always restore stdout/stderr
          os.dup2(old_stdout, 1)
          os.dup2(old_stderr, 2)
          os.close(old_stdout)
          os.close(old_stderr)

      return result

  return wrapper




def asilent(func):
  """Decorator for async functions."""
  @functools.wraps(func)
  async def wrapper(*args, **kwargs):
      old_stdout = os.dup(1)
      old_stderr = os.dup(2)

      try:
          devnull = os.open(os.devnull, os.O_WRONLY)
          os.dup2(devnull, 1)
          os.dup2(devnull, 2)
          os.close(devnull)

          result = await func(*args, **kwargs)

      finally:
          os.dup2(old_stdout, 1)
          os.dup2(old_stderr, 2)
          os.close(old_stdout)
          os.close(old_stderr)

      return result

  return wrapper
