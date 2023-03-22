from dataclasses import dataclass
from enum import Enum, auto
from common import Location, MarnError
from io import TextIOBase
from typing import Generator, Any, TypeVar, Generic
import string


### Token types ###

@dataclass
class Token:
    location : Location

@dataclass
class StringToken(Token):
    value : str

@dataclass
class NatToken(Token):
    value : int

@dataclass
class IntToken(Token):
    value : int

@dataclass
class RatToken(Token):
    numerator : int
    denominator : int

@dataclass
class CommentToken(Token):
    content : str

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
    OPEN_PAREN = auto()
    CLOSE_PAREN = auto()
    DOUBLE_DASH = auto()
    OPEN_BRACKET = auto()
    CLOSE_BRACKET = auto()
    OPEN_BRACE = auto()
    CLOSE_BRACE = auto()
    EOT = auto()

keywords = {
    ':': KeywordEnum.COLON,
    ';': KeywordEnum.SEMICOLON,
    'match:': KeywordEnum.MATCH,
    'case:': KeywordEnum.CASE,
    'loop;': KeywordEnum.LOOP,
    'type:': KeywordEnum.TYPE,
    'alias:': KeywordEnum.ALIAS,
    '(': KeywordEnum.OPEN_PAREN,
    ')': KeywordEnum.CLOSE_PAREN,
    '--': KeywordEnum.DOUBLE_DASH,
    '[': KeywordEnum.OPEN_BRACKET,
    ']': KeywordEnum.CLOSE_BRACKET,
    '{': KeywordEnum.OPEN_BRACE,
    '}': KeywordEnum.CLOSE_BRACE,
}

@dataclass
class KeywordToken(Token):
    keyword : KeywordEnum

class NumberedKeywordEnum(Enum):
    TUPLE = auto()
    PACK = auto()
    UNPACK = auto()

numbered_keywords = {
    'Tuple': NumberedKeywordEnum.TUPLE,
    'pack': NumberedKeywordEnum.PACK,
    'unpack': NumberedKeywordEnum.UNPACK,
}

@dataclass
class NumberedKeywordToken(Token):
    keyword : NumberedKeywordEnum
    count : int


### Errors ###

@dataclass
class UnclosedStringError(MarnError):
    location : Location


### Stream ###

@dataclass
class Stream:
    stream : TextIOBase
    lookahead : str = None
    location : Location = field(default_factory = lambda: Location(0, 0, 0))

    def __post_init__(self) -> None:
        self.lookahead = self.stream.read(1)

    def consume_char(self) -> str:
        if self.lookahead != '':
            if self.lookahead == '\n':
                self.location = self.location.next_row()
            else:
                self.location = self.location.next_column()
            self.lookahead = self.stream.read(1)
        return self.lookahead


### Token generator modifiers ###

def exclude(token_type, generator) -> Generator[Token, None, None]:
    for token in generator:
        if not isinstance(token, token_type):
            yield token
        else:
            match token:
                case KeywordToken(keyword=KeywordEnum.EOT):
                    return

T = TypeVar('T')

@dataclass
class BufferedGenerator(Generic[T]):
    generator : Generator[T, None, Any]
    lookahead : T | None = None

    def __iter__(self) -> Generator[T, None, None]:
        return self

    def __next__(self) -> T:
        self.lookahead = next(self.generator)
        return self.lookahead


### Lexer ###

def tokenize(stream, errors) -> Generator[Token, None, None]:
    stream = Stream(stream)
    consume_whitespace(stream)
    while stream.lookahead:
        yield (try_parse_comment_or_word(stream)
               or try_parse_string(stream, errors)
               or try_parse_nat_or_word(stream)
               or try_parse_negative_or_word(stream)
               or try_parse_number_or_numbered_word(stream)
               or parse_word(stream, [], stream.location))
        consume_whitespace(stream)
    while True:
        yield KeywordToken(stream.location, KeywordEnum.EOT)


### Helper functions ###

def consume_whitespace(stream) -> None:
    while stream.lookahead in list(string.whitespace):
        stream.consume_char()


whitespace = list(string.whitespace) + ['']


def try_parse_comment_or_word(stream) -> None | Token:
    if stream.lookahead != '\\':
        return None
    start = stream.location
    if stream.consume_char() not in whitespace:
        return parse_word(stream, ['\\'], start)
    content = [stream.lookahead]
    while (c := stream.consume_char()) not in ('\n', ''):
        content.append(c)
    return CommentToken(start, ''.join(content))

1
escapes = {
    'n' : '\n',
    'b' : '\b',
    'r' : '\r',
    't' : '\t',
}

def try_parse_string(stream, errors) -> None | Token:
    if stream.lookahead != '"':
        return None
    value = []
    start = stream.location
    while (c := stream.consume_char()) not in ('"', ''):
        if c == '\\':
            c = stream.consume_char()
            if c in escapes: c = escapes[c]
        value.append(c)
    if stream.lookahead == '':
        errors.append(UnclosedStringError(start))
    else:
        stream.consume_char()
    return StringToken(start, ''.join(value))


def try_parse_nat_or_word(stream) -> None | Token:
    if stream.lookahead != '+':
        return None
    start = stream.location
    parsed = ['+']
    stream.consume_char()
    n_parsed, value = parse_digits(stream, parsed)
    if stream.lookahead in whitespace and n_parsed:
        return NatToken(start, value)
    return parse_word(stream, parsed, start)


def try_parse_negative_or_word(stream) -> None | Token:
    if stream.lookahead != '-':
        return None
    start = stream.location
    parsed = ['-']
    stream.consume_char()
    n_parsed, numerator = parse_digits(stream, parsed)
    if stream.lookahead in whitespace and n_parsed:
        return IntToken(start, -numerator)
    if not n_parsed or stream.lookahead != '/':
        return parse_word(stream, parsed, start)
    parsed.append('/')
    stream.consume_char()
    n_parsed, denominator = parse_digits(stream, parsed)
    if stream.lookahead in whitespace and n_parsed:
        return RatToken(start, -numerator, denominator)
    return parse_word(stream, parsed, start)


def try_parse_number_or_numbered_word(stream) -> None | Token:
    start = stream.location
    parsed = []
    n_parsed, numerator = parse_digits(stream, parsed)
    if not n_parsed: return None
    if stream.lookahead in whitespace:
        return IntToken(start, numerator)
    if stream.lookahead != '/':
        return parse_numbered_word(stream, parsed, start, numerator)
    parsed.append('/')
    stream.consume_char()
    n_parsed, denominator = parse_digits(stream, parsed)
    if stream.lookahead in whitespace and n_parsed:
        return RatToken(start, numerator, denominator)
    return parse_word(stream, parsed, start)


def parse_numbered_word(stream, parsed, start, count) -> Token:
    name = parse_until_whitespace(stream, parsed)
    if name in numbered_keywords:
        return NumberedKeywordToken(start, numbered_keywords[name], count)
    return parse_word(stream, parsed, start)


def parse_word(stream, parsed, start) -> Token:
    parse_until_whitespace(stream, parsed)
    name = ''.join(parsed)
    if name in keywords:
        return KeywordToken(start, keywords[name])
    return NameToken(start, name)


def parse_digits(stream, parsed) -> (int, int):
    value = 0
    n_parsed = 0
    while stream.lookahead in list(string.digits):
        value *= 10
        value += int(stream.lookahead)
        n_parsed += 1
        parsed.append(stream.lookahead)
        stream.consume_char()
    return n_parsed, value


def parse_until_whitespace(stream, parsed) -> str:
    value = []
    while stream.lookahead not in whitespace:
        value.append(stream.lookahead)
        parsed.append(stream.lookahead)
        stream.consume_char()
    return ''.join(value)
