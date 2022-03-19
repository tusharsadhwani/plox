from __future__ import annotations

import os.path
from textwrap import dedent

import pytest
from pytest import CaptureFixture

from pylox.interpreter import Interpreter
from pylox.lexer import Lexer
from pylox.lox_types import LoxType
from pylox.nodes import (
    Assignment,
    Binary,
    Block,
    Expr,
    ExprStmt,
    Grouping,
    Literal,
    Print,
    Program,
    VarDeclaration,
    Variable,
)
from pylox.parser import Parser
from pylox.resolver import Resolver
from pylox.tokens import Token, TokenType


@pytest.mark.parametrize(
    ("tree", "expected"),
    (
        (
            Binary(
                left=Literal(value=2.0),
                operator=Token(token_type=TokenType.PLUS, string="+", value=None),
                right=Binary(
                    left=Literal(value=3.0),
                    operator=Token(token_type=TokenType.STAR, string="*", value=None),
                    right=Literal(value=5.0),
                ),
            ),
            17.0,
        ),
        # TODO: add more tests
    ),
)
def test_interpreter_expr(tree: Expr, expected: LoxType) -> None:
    output = Interpreter().evaluate(tree)
    assert output == expected


@pytest.mark.parametrize(
    ("tree", "output"),
    (
        (
            Program(
                body=[
                    VarDeclaration(
                        name=Token(TokenType.IDENTIFIER, "greeting"),
                        initializer=Literal("hello lox!"),
                    ),
                    Print(Variable(Token(TokenType.IDENTIFIER, "greeting"))),
                ]
            ),
            "hello lox!",
        ),
        (
            Program(
                body=[
                    VarDeclaration(
                        name=Token(TokenType.IDENTIFIER, "a"),
                        initializer=Literal("Something"),
                    ),
                    VarDeclaration(
                        name=Token(TokenType.IDENTIFIER, "b"),
                        initializer=Literal("Another thing"),
                    ),
                    ExprStmt(
                        Assignment(
                            name=Token(TokenType.IDENTIFIER, "a"),
                            value=Assignment(
                                name=Token(TokenType.IDENTIFIER, "b"),
                                value=Binary(
                                    left=Literal(2.0),
                                    operator=Token(TokenType.PLUS, "+"),
                                    right=Literal(3.0),
                                ),
                            ),
                        ),
                    ),
                    Print(Variable(Token(TokenType.IDENTIFIER, "a"))),
                    Print(Variable(Token(TokenType.IDENTIFIER, "b"))),
                ],
            ),
            "5.0\n5.0",
        ),
        (
            Program(
                body=[
                    VarDeclaration(
                        name=Token(TokenType.IDENTIFIER, "a", index=4),
                        initializer=Literal(value="ga"),
                    ),
                    VarDeclaration(
                        name=Token(TokenType.IDENTIFIER, "b", index=18),
                        initializer=Literal(value="gb"),
                    ),
                    VarDeclaration(
                        name=Token(TokenType.IDENTIFIER, "c", index=32),
                        initializer=Literal(value="gc"),
                    ),
                    Block(
                        body=[
                            VarDeclaration(
                                name=Token(TokenType.IDENTIFIER, "a", index=49),
                                initializer=Literal(value="ea"),
                            ),
                            VarDeclaration(
                                name=Token(TokenType.IDENTIFIER, "b", index=63),
                                initializer=Literal(value="eb"),
                            ),
                            Block(
                                body=[
                                    VarDeclaration(
                                        name=Token(TokenType.IDENTIFIER, "a", index=85),
                                        initializer=Literal(value="la"),
                                    ),
                                    Print(
                                        Variable(
                                            Token(TokenType.IDENTIFIER, "a", index=101)
                                        )
                                    ),
                                    Print(
                                        Variable(
                                            Token(TokenType.IDENTIFIER, "b", index=110)
                                        )
                                    ),
                                    Print(
                                        Variable(
                                            Token(TokenType.IDENTIFIER, "c", index=119)
                                        )
                                    ),
                                ]
                            ),
                            Print(
                                Variable(Token(TokenType.IDENTIFIER, "a", index=134))
                            ),
                            Print(
                                Variable(Token(TokenType.IDENTIFIER, "b", index=143))
                            ),
                            Print(
                                Variable(Token(TokenType.IDENTIFIER, "c", index=152))
                            ),
                        ]
                    ),
                    Print(Variable(Token(TokenType.IDENTIFIER, "a", index=163))),
                    Print(Variable(Token(TokenType.IDENTIFIER, "b", index=172))),
                    Print(Variable(Token(TokenType.IDENTIFIER, "c", index=181))),
                ]
            ),
            "la\neb\ngc\nea\neb\ngc\nga\ngb\ngc",
        ),
        (
            Program(
                body=[
                    Print(
                        Binary(
                            left=Literal(value=0.0),
                            operator=Token(TokenType.OR, "or"),
                            right=Binary(
                                left=Binary(
                                    left=Literal(value=True),
                                    operator=Token(TokenType.AND, "and"),
                                    right=Literal(value=3.0),
                                ),
                                operator=Token(TokenType.AND, "and"),
                                right=Grouping(
                                    Binary(
                                        left=Literal(value=7.0),
                                        operator=Token(TokenType.OR, "or"),
                                        right=Binary(
                                            left=Literal(value=0.0),
                                            operator=Token(TokenType.SLASH, "/"),
                                            right=Literal(value=0.0),
                                        ),
                                    )
                                ),
                            ),
                        )
                    )
                ]
            ),
            "7.0",
        )
        # TODO: add more tests
    ),
)
def test_interpreter(
    tree: Program,
    output: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    interpreter = Interpreter()

    resolver = Resolver(interpreter)
    resolver.visit(tree)

    interpreter.visit(tree)

    stdout, stderr = capsys.readouterr()
    assert stdout.rstrip() == output
    assert stderr == ""


# TODO: add failing tests


@pytest.mark.parametrize(
    ("filename", "output"),
    (
        (
            "simple.lox",
            """\
            Hello
            5.0
            false
            27.0
            """,
        ),
        (
            "operators.lox",
            """\
            true
            false
            false
            -3.0
            0.0
            true
            false
            0.25
            0.5
            abcdef
            """,
        ),
        (
            "control_flow.lox",
            """\
            Number is positive
            Number is small
            Should run
            2.0
            4.0
            8.0
            0.0
            1.0
            2.0
            10.0
            20.0
            """,
        ),
        (
            "native_functions.lox",
            """\
            <native function 'clock'>
            true
            true
            """,
        ),
        (
            "functions.lox",
            """\
            <function 'hello'>
            Hello
            Hello
            1.0
            2.0
            3.0
            30.0
            70.0
            Counter starting
            1.0
            2.0
            360.0
            nil
            1.0
            """,
        ),
        (
            "static_resolution.lox",
            """\
            global
            global
            global
            """,
        ),
        (
            "classes.lox",
            """\
            <class 'C'>
            10.0
            The German chocolatecake is delicious
            foo
            bob
            alice
            """,
        ),
        (
            "inheritance.lox",
            """\
            Fry until golden brown
            C
            D
            A
            """,
        ),
        (
            "escapes.lox",
            """\
            a
            \tb
            a\\b\\c\\d
            'hello'
            "This is lox's lexer"
            """,
        ),
    ),
)
def test_interpreter_files(
    filename: str,
    output: str,
    capsys: CaptureFixture[str],
) -> None:
    test_dir = os.path.join(os.path.dirname(__file__), "testdata")
    filepath = os.path.join(test_dir, filename)
    with open(filepath) as file:
        source = file.read()

    tokens = Lexer(source).tokens
    parser = Parser(tokens)
    program, errors = parser.parse()
    assert not errors

    interpreter = Interpreter()

    resolver = Resolver(interpreter)
    resolver.visit(program)

    interpreter.visit(program)

    stdout, stderr = capsys.readouterr()
    assert stdout.rstrip() == dedent(output).rstrip()
    assert stderr == ""


# TODO: add benchmarks, eg. recusrive fibonacci(25)
