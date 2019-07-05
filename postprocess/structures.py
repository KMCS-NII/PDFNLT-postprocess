"""
The basic structures of texts.
"""

# libraries
from lxml import etree


# the module
class Paragraph:
    def __init__(self, sec_id, _id, sec_name, box_name, words, backup_words):
        self.sec_id = sec_id
        self._id = _id
        self.sec_name = sec_name
        self.box_name = box_name
        self.words = words
        self.backup_words = backup_words


class Word:
    def __init__(self, _id, text, node=None, start=None):
        self._id = _id
        self.text = text
        self.node = node
        self.start = start


class Sentence:
    def __init__(self, _id, sec_name, box_name, text, words):
        self._id = _id
        self.sec_name = sec_name
        self.box_name = box_name
        self.text = text
        self.words = words


class Document:
    def __init__(self, fn, parser=None):
        self.filename = fn
        self.tree = etree.parse(fn, parser=parser)
