from dataclasses import dataclass, field
from enum import Enum, auto
from io import TextIOBase
from typing import Optional, Generator, Any
from fractions import Fraction

import re

# Samples and ideas #

'''

type: from to FunctionType ;

type: a List :
    a List a Cons
    Empty ;

alias: Stack
    Value List ;

type: Value :
    Concrete
    Any ;

type: Expr :
    Expr List Block
    FunctionType Function
    Recursive
    Case List Type Match



: typecheck-block ( block -- type )
    id-type swap match:
        case: Empty ;
        case: Cons
            swap dip:
                 compose ;
        loop;

'''


# Data types #

@dataclass
class Location:
    row : int
    column : int
    position : int

    def copy(self):
        return Location(self.row, self.column, self.position)

@dataclass
class MarnError: ...

@dataclass
class UnclosedStringError(MarnError):
    location : Location

@dataclass
class UnclosedCommentError(MarnError):
    location : Location

@dataclass
class ZeroDenominatorError(MarnError):
    location : Location
    numerator : int
    denominator : int

@dataclass
class BadTopLevelTokenError(MarnError):
    token : 'Token'

@dataclass
class RedefinitionError(MarnError):
    duplicate : 'Node'
    original : 'Node'

@dataclass
class UnnamedWordError(MarnError):
    location : Location

@dataclass
class UnclosedWordError(MarnError):
    location : Location

@dataclass
class BadExpressionTokenError(MarnError):
    token : 'Token'

@dataclass
class EmptyMatchError(MarnError):
    location : Location

@dataclass
class UnnamedCaseError(MarnError):
    location : Location

@dataclass
class UnclosedDipError(MarnError):
    location : Location


# Lexing data types #

@dataclass
class Stream:
    stream : TextIOBase
    lookahead : Optional[str] = None
    location : Location = field(default_factory = lambda: Location(0, 0, 0))

    def __post_init__(self):
        self.lookahead = self.stream.read(1)

    def consume_char(self) -> str:
        if self.lookahead != '':
            if self.lookahead == '\n':
                self.location.row += 1
                self.location.column = 0
            else:
                self.location.column += 1
            self.location.position += 1
        self.lookahead = self.stream.read(1)
        return self.lookahead

@dataclass
class Token:
    location : Location

@dataclass
class LiteralToken(Token):
    value : str

@dataclass
class CommentToken(Token):
    value : str

@dataclass
class NameToken(Token):
    name : str

class KeywordEnum(Enum):
    COLON = auto()
    SEMICOLON = auto()
    MATCH = auto()
    CASE = auto()
    LOOP = auto()
    TYPE = auto()
    ALIAS = auto()
    OPEN_BRACKET = auto()
    CLOSE_BRACKET = auto()
    EOF = auto()
    DIP = auto()

keywords = {
    ':': KeywordEnum.COLON,
    ';': KeywordEnum.SEMICOLON,
    'match:': KeywordEnum.MATCH,
    'case:': KeywordEnum.CASE,
    'loop;': KeywordEnum.LOOP,
    'type:': KeywordEnum.TYPE,
    'alias:': KeywordEnum.ALIAS,
    'dip:': KeywordEnum.DIP,
    '[': KeywordEnum.OPEN_BRACKET,
    ']': KeywordEnum.CLOSE_BRACKET,
}

@dataclass
class KeywordToken(Token):
    keyword : KeywordEnum

# Lexer #

'''

token   := number | bool | string | keyword | word
number  := int [ '/' nat ]
int     := [ '-' ] nat
nat     := '0' | ( '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9' ) [ digits ]
digits  := '0' | '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9'
bool    := 'true' | 'false'
keyword := ':' | ';' | 'match:' | 'case:' | 'loop;' | 'type:'
string  := '"' [ string-body ] '"'
word    := non-whitespace [ word ]

'''

whitespace = ' \r\n\t'

def consume_whitespace(stream) -> None:
    while stream.lookahead in whitespace and stream.lookahead != '':
        stream.consume_char()

def consume_word(stream) -> str:
    ans = ''
    while stream.lookahead not in whitespace and stream.lookahead != '':
        ans += stream.lookahead
        stream.consume_char()
    return ans


escapes = {
    'n': '\n',
    't': '\t',
    'b': '\b',
    'a': '\a',
}

def consume_string(stream, errors) -> LiteralToken:
    ans = ''
    string_start = stream.location.copy()
    while stream.consume_char() != '"':
        if stream.lookahead == '':
            errors.append(UnclosedStringError(string_start))
            return LiteralToken(string_start, ans)
        elif stream.lookahead == '\\':
            stream.consume_char()
            if stream.lookahead == '':
                errors.append(UnclosedStringError(string_start))
                return LiteralToken(string_start, ans)
            elif stream.lookahead in escapes:
                ans += escapes[stream.lookahead]
            else:
                ans += stream.lookahead
        else:
            ans += stream.lookahead
    stream.consume_char()
    return LiteralToken(string_start, ans)


def consume_comment(stream, errors) -> CommentToken:
    ans = ''
    comment_start = stream.location.copy()
    depth = 1
    while stream.consume_char():
        if stream.lookahead == '(':
            depth += 1
        elif stream.lookahead == ')':
            depth -= 1
            if depth <= 0:
                stream.consume_char()
                return CommentToken(comment_start, ans)
        ans += stream.lookahead
    errors.append(UnclosedCommentError(comment_start))
    return CommentToken(comment_start, ans)


int_regex = r'[+-]?[0-9]+'
rat_regex = f'({int_regex})/([0-9]+)'
def parse_rat(match, location, errors) -> Optional[Fraction]:
    if int(match.group(2)) == 0:
        errors.append(ZeroDenominatorError(location, match.group(1),
                                           match.group(2)))
        return
    return LiteralToken(location, Fraction(int(match.group(1)),
                                           int(match.group(2))))


def lexeme_generator(stream, errors) -> Generator[Token, None, None]:
    stream = Stream(stream)
    consume_whitespace(stream)
    while stream.lookahead:
        location = stream.location.copy()
        if stream.lookahead == '"':
            yield consume_string(stream, errors)
        elif stream.lookahead == '(':
            yield consume_comment(stream, errors)
        else:
            word = consume_word(stream)
            if word == 'true':
                yield LiteralToken(location, True)
            elif word == 'false':
                yield LiteralToken(location, False)
            elif word in keywords:
                yield KeywordToken(location, keywords[word])
            elif match := re.fullmatch(rat_regex, word):
                if rat := parse_rat(match, location, errors): yield rat
            elif re.fullmatch(int_regex, word):
                yield LiteralToken(location, int(word))
            else:
                yield NameToken(location, word)
        consume_whitespace(stream)
    yield KeywordToken(stream.location, KeywordEnum.EOF)


# AST types #

@dataclass
class BufferedGenerator:
    generator : Generator[Any, None, None]
    peek = None
    stopped = False

    def __post_init__(self):
        try:
            self.peek = next(self.generator)
        except StopIteration:
            self.stopped = True

    def __next__(self):
        if self.stopped: raise StopIteration
        prev = self.peek
        try:
            self.peek = next(self.generator)
        except StopIteration:
            self.stopped = True
        return prev

    def __iter__(self):
        return self

@dataclass
class Node:
    location : Location

@dataclass
class CommentNode(Node):
    value : str

@dataclass
class LiteralNode(Node):
    value : Any

@dataclass
class NameNode(Node):
    name : str

@dataclass
class CaseNode(Node):
    constructor : 'NameNode | ConstructorNode'
    body : list[Node]

@dataclass
class MatchNode(Node):
    cases : list[CaseNode]

@dataclass
class DipNode(Node):
    body : list[Node]

@dataclass
class WordNode(Node):
    name : str
    body : list
    in_type = None
    out_type = None

@dataclass
class ConstructorNode(Node):
    name : str
    args : list
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
    body : list

@dataclass
class AST:
    words : dict[str, WordNode] = field(default_factory=dict)
    types : dict[str, TypeNode] = field(default_factory=dict)
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

# AST building #

'''

program         := ( definition | comment ) [ program ]
exprs           := ( literal | match | dip | name | comment ) [ exprs ]
definition      := word | type | alias
literal         := int | nat | string | bool | list
match           := 'match:' cases
cases           := 'case:' exprs ';' [ cases ]
word            := ':' name [ exprs ] ';'
type            := 'type:' [ names ] name ':' constructors ';'
constructors    := [ names ] name [ '|' constructors ]
alias           := 'alias:' [ names ] name ':' names ';'
list            := '[' [ literals ] ']'
names           := name [ names ]

'''

def parse_case(generator, location, errors) -> Optional[CaseNode]:
    match generator.peek:
        case NameToken(name=constructor): next(generator)
        case _:
            errors.append(UnnamedCaseError(location))
            name = None
    body = parse_expressions(generator, errors, UnclosedWordError)
    if constructor:
        return CaseNode(location, constructor, body)
    

def parse_match(generator, location, errors) -> Optional[MatchNode]:
    cases = []
    caseless = True
    while True:
        match generator.peek:
            case KeywordToken(location=case_location, keyword=KeywordEnum.CASE):
                next(generator)
                if case := parse_case(generator, location, errors):
                    cases.append(case)
                caseless = False
            case _:
                break
    if caseless:
        errors.append(EmptyMatchError(location))
    else:
        return MatchNode(location, cases)

def parse_dip(generator, location, errors) -> DipNode:
    return DipNode(location, parse_expressions(generator, errors,
                                               UnclosedDipError))

def parse_expressions(generator, errors, EOF_error) -> list[Node]:
    exprs = []
    while True:
        match generator.peek:
            case KeywordToken(keyword=KeywordEnum.SEMICOLON):
                next(generator)
                return exprs
            case LiteralToken(location=location, value=value):
                next(generator)
                exprs.append(LiteralNode(location, value))
            case KeywordToken(location=location, keyword=KeywordEnum.MATCH):
                next(generator)
                if match := parse_match(generator, location, errors):
                    exprs.append(match)
            case KeywordToken(location=location, keyword=KeywordEnum.DIP):
                next(generator)
                exprs.append(parse_dip(generator, location, errors))
            case NameToken(location=location, name=name):
                next(generator)
                exprs.append(NameNode(location, name))
            case CommentToken(location=location, value=value):
                next(generator)
                exprs.append(CommentNode(location, value))
            case KeywordToken(keyword=KeywordEnum.EOF):
                errors.append(EOF_error(location))
                return exprs
            case token:
                next(generator)
                errors.append(BadExpressionTokenError(token))

def parse_word(generator, location, errors) -> Optional[WordNode]:
    match generator.peek:
        case NameToken(name=name): next(generator)
        case _:
            errors.append(UnnamedWordError(location))
            name = None
    body = parse_expressions(generator, errors, UnclosedWordError)
    if name:
        return WordNode(location, name, body)


def parse_type(generator, location, errors) -> Optional[TypeNode]: ...
def parse_alias(generator, location, errors) -> Optional[AliasNode]: ...

def parse_tokens(generator, errors) -> AST:
    generator = BufferedGenerator(generator)
    ast = AST()
    for token in generator:
        match token:
            case CommentToken(location=location, value=value):
                ast.sequential.append(CommentNode(location, value))
            case KeywordToken(location=location, keyword=KeywordEnum.COLON):
                if not (word := parse_word(generator, location, errors)):
                    continue
                if duplicate := ast.word(word.name):
                    errors.append(RedefinitionError(word, duplicate))
                    continue
                ast.words[word.name] = word
                ast.sequential.append(word)
            case KeywordToken(location=location, keyword=KeywordEnum.TYPE):
                if not (new_type := parse_type(generator, location, errors)):
                    continue
                if duplicate := ast.type(new_type.name):
                    errors.append(RedefinitionError(new_type, duplicate))
                    continue
                ast.types[new_type.name] = new_type
                for constructor in new_type.constructors:
                    if duplicate := ast.word(constructor.name):
                        errors.append(RedefinitionError(constructor, duplicate))
                        continue
                    ast.constructors[constructor.name] = constructor
                ast.sequential.append(new_type)
            case KeywordToken(location=location, keyword=KeywordEnum.ALIAS):
                if not (alias := parse_alias(generator, location, errors)):
                    continue
                if duplicate := ast.type(alias.name):
                    errors.append(RedefinitionError(alias, duplicate))
                    continue
                ast.aliases[alias.name] = alias
                ast.sequential.append(alias)
            case KeywordToken(location=location, keyword=KeywordEnum.EOF): ...
            case _:
                errors.append(BadTopLevelTokenError(token))
                while True:
                    match generator.peek:
                        case KeywordToken(location=location,
                                          keyword=KeywordEnum.COLON
                                                 |KeywordEnum.TYPE
                                                 |KeywordEnum.ALIAS
                                                 |KeywordEnum.EOF):
                                 break
                        case _: next(generator)
    return ast


# Testing and Debug

from io import StringIO

def test(s : str) -> AST | list[MarnError]:
    e = []
    l = lexeme_generator(StringIO(s), e)
    if e: return e
    a = parse_tokens(l, e)
    if e: return e
    return a
