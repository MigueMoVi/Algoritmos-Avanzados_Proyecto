import os
import sys

from .cli import main

try:
    main()
except BrokenPipeError:                 # salida cortada (p. ej. con | head): terminar sin error
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stdout.fileno())
    sys.exit(0)
