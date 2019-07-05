"""
Exceptions
"""

class PostprocessError(Exception):
    """Error class for postprocess"""

class AlreadyTaggedError(PostprocessError):
    """An error which occured trying to tag already math-tagged xhtml"""
