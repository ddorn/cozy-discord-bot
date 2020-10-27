"""
This module defines all the custom Exceptions used in this project.
"""

__all__ = ["EpflError"]


class EpflError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return self.msg

