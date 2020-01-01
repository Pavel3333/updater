# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: ./JSONx/parser.py
# Compiled at: 2019-10-06 04:02:22
__author__ = 'Alex'
from lexer import *
from ast import *
import exception

class Parser(object):

    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0
        self.length = len(tokens)

    def error(self, message, *args):
        line, col = self.token.line_col
        raise exception.ParserException(message.format(*args), (line, col))

    @property
    def token(self):
        """
        peek current token
        :rtype : JSONxToken
        """
        return self.tokens[self.position] if self.position < self.length else None

    def expect(self, expected_type):
        """
        :rtype : JSONxToken | None
        """
        token = self.tokens[self.position] if self.position < self.length else None
        if not token or token.type != expected_type:
            return
        else:
            self.position += 1
            return token

    def ensure(self, expected_type, message, *args):
        """
        raise ParserException when fail
        :rtype : JSONxToken | None
        """
        token = self.tokens[self.position] if self.position < self.length else None
        if not token or token.type != expected_type:
            self.error(message, *args)
        self.position += 1
        return token


class JSONxParser(Parser):

    def parse_keyword(self):
        token = self.expect(Type.KEYWORD)
        if not token:
            return None
        elif token.value == 'true':
            return TrueNode()
        elif token.value == 'false':
            return FalseNode()
        else:
            return NullNode() if token.value == 'null' else None

    def parse_number(self):
        token = self.expect(Type.NUMBER)
        if token:
            try:
                return NumberNode(int(token.value))
            except ValueError:
                return NumberNode(float(token.value))

    def parse_string(self):
        token = self.expect(Type.STRING)
        return StringNode(token.value) if token else None

    def parse_object(self):
        left_bracket = self.expect(Type.LEFT_CURLY_BRACKET)
        if not left_bracket:
            return None
        else:
            right_bracket = self.expect(Type.RIGHT_CURLY_BRACKET)
            if right_bracket:
                return ObjectNode([])
            pairs = self.parse_pairs()
            self.ensure(Type.RIGHT_CURLY_BRACKET, 'OBJECT: "}}" expected, got "{}"', self.token.value)
            return ObjectNode(pairs)

    def parse_pairs(self):
        pairs = []
        while True:
            if pairs and not self.expect(Type.COMMA):
                break
            pair = self.parse_pair()
            if not pair:
                self.error('PAIR: <pair> expected, got "{}"', self.token.value)
            pairs += (pair,)

        return pairs

    def parse_pair(self):
        key = self.parse_string()
        if not key:
            return None
        else:
            self.ensure(Type.COLON, 'PAIR: ":" expected, got "{}"', self.token.value)
            value = self.parse_value()
            if not value:
                self.error('PAIR: <value> expected, got "{}"', self.token.value)
            return PairNode(key, value)

    def parse_array(self):
        left_bracket = self.expect(Type.LEFT_SQUARE_BRACKET)
        if not left_bracket:
            return None
        else:
            right_bracket = self.expect(Type.RIGHT_SQUARE_BRACKET)
            if right_bracket:
                return ArrayNode([])
            elements = self.parse_elements()
            self.ensure(Type.RIGHT_SQUARE_BRACKET, 'ARRAY: "]" expected, got "{}"', self.token.value)
            return ArrayNode(elements)

    def parse_elements(self):
        elements = []
        while True:
            if elements and not self.expect(Type.COMMA):
                break
            value = self.parse_value()
            if not value:
                self.error('ARRAY: <value> expected, got "{}"', self.token.value)
            elements += (value,)

        return elements

    def parse_reference(self):
        if not self.expect(Type.DOLLAR):
            return
        else:
            self.ensure(Type.LEFT_CURLY_BRACKET, 'REFERENCE: <{{> expected, got {}', self.token.value)
            object_path = self.expect(Type.STRING)
            file_path = None
            if not object_path:
                self.error('REFERENCE: <string> expected, got {}', self.token)
            if self.expect(Type.COLON):
                file_path = object_path
                object_path = self.expect(Type.STRING)
            self.ensure(Type.RIGHT_CURLY_BRACKET, 'REFERENCE: <}}> expected, got', self.token.value)
            file_path = file_path and file_path.value
            return ReferenceNode(file_path, object_path.value)

    def parse_value(self):
        token = self.token
        if token.type == Type.LEFT_CURLY_BRACKET:
            return self.parse_object()
        if token.type == Type.LEFT_SQUARE_BRACKET:
            return self.parse_array()
        if token.type == Type.STRING:
            return self.parse_string()
        if token.type == Type.NUMBER:
            return self.parse_number()
        if token.type == Type.KEYWORD:
            return self.parse_keyword()
        return self.parse_reference() if token.type == Type.DOLLAR else None

    def parse(self):
        value = self.parse_value()
        self.ensure(Type.EOF, 'PARSER: <EOF> expected, got "{}"', self.token.value)
        return value


def parse(tokens):
    parser = JSONxParser(tokens)
    return parser.parse()
