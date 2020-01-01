# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: ./JSONx/__init__.py
# Compiled at: 2019-10-06 04:02:22
__author__ = 'Alex'
import lexer
import parser
import utils
import JSONx.ast
from exception import JSONxException

def parse(source):
    visitor = JSONx.ast.JSONxVisitor()
    tokens = lexer.tokenize(source)
    json_ast = parser.parse(tokens)
    return visitor.visit(json_ast)
