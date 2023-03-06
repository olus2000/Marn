================================================================================
                                      Marn
================================================================================

A language that will hopefully be accepted as the project for the TKOM course.
Clearly unfinished.


Usage
=====

In the `proj.py`_ file there are two functions (for now):

``lexeme_generator`` : ``TextIOStream, list -> Generator[Token]`` :
    Consumes the text stream and returns a generator of tokens. Any lexing
    errors will be appended to the list.

``parse_tokens`` : ``Generator[Token], list -> AST`` :
    Consumes the generator and returns the AST without resolving names. All
    unresolved names are ``NameNode`` instances. Parsing errors are appended to
    the list. Unfinished.

There is also a temporary helper method ``test`` that takes a string and tries
to parse it, returning an error list if any errors are encountered.


Language sample
===============

For now it doesn't execute anything yet, but if you input this implementation of
fibonacci into ``test`` it should spit out the AST for it::

    : fib ( n -- f(n) )
      0 1 rot match:
        case: Succ dip: over + swap ; ;
        case: Zero drop ; ;
