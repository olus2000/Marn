from common import Location, MarnError
from lexer import (
        Token, StringToken, NatToken, IntToken, RatToken, CommentToken,
        NameToken, KeywordEnum, KeywordToken, NumberedKeywordEnum,
        NumberedKeywordToken, exclude, BufferedGenerator
)
from dataclasses import dataclass, field
from typing import Optional, Generator, Any, TypeVar, Generic
from fractions import Fraction


### Node types ###

@dataclass
class Node:
    location : Location

@dataclass
class NameNode(Node):
    name : str

@dataclass
class NatNode(Node):
    value : int

@dataclass
class IntNode(Node):
    value : int

@dataclass
class RatNode(Node):
    value : Fraction

@dataclass
class StringNode(Node):
    value : str

@dataclass
class ListNode(Node):
    value : list[Node]

@dataclass
class QuoteNode(Node):
    value : list[Node]

@dataclass
class FuncTypeNode(Node):
    in_type : list[Node]
    out_type : list[Node]

@dataclass
class WordNode(Node):
    name : str
    body : list[Node]

@dataclass
class ConstructorNode(Node):
    name : str
    args : list[Node]
    type : 'TypeNode'

@dataclass
class TypeNode(Node):
    name : str
    variables : list[str]
    constructors : list[ConstructorNode] = field(default_factory=list)

@dataclass
class AliasNode(Node):
    name : str
    variables : list[str]
    body : list[Node]

@dataclass
class PrimitiveNode(Node):
    name : str

class PrimitiveWordNode(PrimitiveNode): ...
class PrimitiveConstructorNode(PrimitiveNode): ...
class PrimitiveTypeNode(PrimitiveNode): ...
class PrimitiveAliasNode(PrimitiveNode): ...

@dataclass
class AST:
    words : dict[str, WordNode | PrimitiveWordNode] =
                field(default_factory=dict)
    types : dict[str, TypeNode | PrimitiveTypeNode] = field(default_factory=dict)
    aliases : dict[str, AliasNode] = field(default_factory=dict)
    constructors : dict[str, ConstructorNode] = field(default_factory=dict)
    sequential : list[Node] = field(default_factory=list)

    def word(self, name: str) -> WordNode | ConstructorNode:
        if name in self.words:
            return self.words[name]
        if name in self.constructors:
            return self.constructors[name]
        return None

    def type(self, name: str) -> TypeNode | AliasNode:
        if name in self.types:
            return self.types[name]
        if name in self.aliases:
            return self.aliases[name]
        return None

### Errors ###


### First pass ###


### Name resolution ###
