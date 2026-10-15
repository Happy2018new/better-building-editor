# -*- coding: utf-8 -*-
"""Close the automatically opened workspace in the isolated test game."""
from modern_projection.pyreact import navigator
_result = {'was_open': navigator.contains('modern_projection_workspace'), 'accepted': navigator.pop()}
