# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: ./JSONx/lexer.py
# Compiled at: 2019-10-06 04:02:22
import re
import exception
import utils

class Type(object):
    IGNORE = None
    EOF = 'EOF'
    LEFT_CURLY_BRACKET = 'LEFT_CURLY_BRACKET'
    RIGHT_CURLY_BRACKET = 'RIGHT_CURLY_BRACKET'
    LEFT_SQUARE_BRACKET = 'LEFT_SQUARE_BRACKET'
    RIGHT_SQUARE_BRACKET = 'RIGHT_SQUARE_BRACKET'
    DOLLAR = 'DOLLAR'
    COLON = 'COLON'
    COMMA = 'COMMA'
    KEYWORD = 'KEYWORD'
    STRING = 'STRING'
    NUMBER = 'NUMBER'
    ID = 'ID'


class JSONxToken(object):

    def __init__(self, token_type, value, pos, source=''):
        self.type = token_type
        self.value = value
        self.position = pos
        self.source = source
        self.__line_col = ()

    @property
    def line_col(self):
        if not self.__line_col:
            self.__line_col = utils.get_position(self.source, self.position)
        return self.__line_col

    def __eq__(self, other):
        return False if not isinstance(other, JSONxToken) else self.type == other.type and self.value == other.value and self.position == other.position

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "JSONxToken(type={} value='{:.50s}' pos={})".format(self.type, self.value.encode('unicode-escape'), self.position)


class JSONxLexer(object):

    def __init__(self, patterns):
        self.groups = {}
        regex_parts = []
        for i, args in enumerate(patterns):
            pattern, tag, handler = (args[0], args[1], args[2]) if len(args) == 3 else (args[0], args[1], None)
            group_name = 'GROUP_{0}_{1}'.format(i, tag)
            self.groups[group_name] = (tag, handler)
            regex_parts.append('(?P<{0}>{1})'.format(group_name, pattern))

        self.parser_regex = re.compile('|'.join(regex_parts), re.UNICODE)
        return

    def parse(self, source):
        result = []
        length = len(source)
        index = 0
        while index < length:
            match = self.parser_regex.match(source, index)
            if match:
                group_name = match.lastgroup
                tag, handler = self.groups[group_name]
                text = match.group(group_name)
                if handler:
                    text = handler(text)
                if tag:
                    result += (JSONxToken(tag, text, index, source),)
            else:
                raise exception.LexerException('Illegal character "{0}"'.format(source[index].encode('unicode-escape')), utils.get_position(source, index))
            index = match.end()

        result += (JSONxToken(Type.EOF, 'EOF', index, source),)
        return result


_patterns = [('[ \\t\\r\\n]+', Type.IGNORE),
 ('//[^\\n]*', Type.IGNORE),
 ('{', Type.LEFT_CURLY_BRACKET),
 ('}', Type.RIGHT_CURLY_BRACKET),
 ('\\[', Type.LEFT_SQUARE_BRACKET),
 ('\\]', Type.RIGHT_SQUARE_BRACKET),
 ('\\$', Type.DOLLAR),
 ('\\:', Type.COLON),
 (',', Type.COMMA),
 ('([+-]?(0|[1-9][0-9]*)(\\.[0-9]*)?([eE][+-]?[0-9]+)?)', Type.NUMBER),
 ('\\b(true|false|null)\\b', Type.KEYWORD),
 ('("(?:[^"\\\\]|\\\\.)*")', Type.STRING, lambda text: utils.decode_escapes(text)[1:-1] if '\\' in text else text[1:-1]),
 ('/\\*(.|\\n)*?\\*/', Type.IGNORE)]
_lexer = JSONxLexer(_patterns)

def tokenize(source):
    return _lexer.parse(source)
