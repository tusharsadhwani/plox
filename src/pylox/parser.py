from __future__ import annotations

import sys
from typing import Literal as LiteralType
from typing import overload

from pylox.errors import LoxError
from pylox.lexer import Lexer
from pylox.nodes import (
    Assignment,
    Binary,
    Block,
    Expr,
    ExprStmt,
    Grouping,
    If,
    Literal,
    Print,
    Program,
    Stmt,
    Unary,
    VarDeclaration,
    Variable,
    While,
)
from pylox.tokens import EOF, Token, TokenType


class ParseError(LoxError):
    def __init__(self, message: str, token: Token) -> None:
        super().__init__(message, token.index)
        self.token = token


class ParseEOFError(ParseError):
    ...


class Parser:
    """
    Current grammar:
        program -> declaration* EOF
        declaration -> var_decl | statement
        var_decl -> "var" IDENTIFIER ("=" expression)? ";"
        statement -> block_stmt
                   | print_stmt
                   | if_stmt
                   | while_stmt
                   | expr_stmt
        block -> "{" declaration* "}"
        print_stmt -> "print" expression ";"
        if_stmt -> "if" "(" expression ")" statement ("else" statement)?
        while_stmt -> "while" "(" expression ")" statement
        expr_stmt -> expression ";"
        expression -> assignment
        assignment -> IDENTIFIER "=" assignment | equality
        equality -> comparison (("==" | "!=") comparison)*
        comparison -> term ((">" | ">=" | "<" | "<=") term)*
        term -> factor (("+" / "-") factor)*
        factor -> unary (("*" / "/") unary)*
        unary -> ("-" | "!") unary | primary
        primary -> NUMBER | STRING | "true" | "false" | "nil" | "(" expression ")"
                | IDENTIFIER
    """

    def __init__(self, tokens: list[Token]) -> None:
        if tokens[-1] != EOF:
            raise ValueError(f"Expected EOF as the last token, found {tokens[-1]}")
        self.tokens = tokens
        self.index = 0

    @property
    def scanned(self) -> int:
        """Returns True if tokens has been fully scanned."""
        if self.index >= len(self.tokens) - 1:
            return True

        return False

    def advance(self) -> None:
        self.index += 1

    def get_token(self) -> Token:
        if self.scanned:
            return EOF

        return self.tokens[self.index]

    def get_index(self) -> int:
        if self.index == 0:
            return self.get_token().index

        return self.previous().index

    def peek_next(self, token_type: TokenType) -> bool:
        token = self.get_token()

        if token is EOF:
            return False

        return token.token_type == token_type

    def match_next(self, *token_types: TokenType) -> bool:
        token = self.get_token()

        if token is EOF:
            return False

        if token.token_type in token_types:
            self.advance()
            return True

        return False

    def previous(self) -> Token:
        if self.index == 0:
            raise RuntimeError("previous() ran at beginning of file")

        return self.tokens[self.index - 1]

    def synchronize(self) -> None:
        """
        Current synchronization process: keep scanning till next statement
        (a.k.a. find a semicolon).
        """
        while not self.scanned and not self.match_next(TokenType.SEMICOLON):
            self.advance()

    @overload
    def parse(
        self, mode: LiteralType["file"] = "file"
    ) -> tuple[Program, list[ParseError]]:
        ...

    @overload
    def parse(self, mode: LiteralType["repl"]) -> Program:
        ...

    def parse(
        self, mode: LiteralType["file", "repl"] = "file"
    ) -> Program | tuple[Program, list[ParseError]]:
        body: list[Stmt] = []
        # Errors are only stored in mode == "file"
        errors: list[ParseError] = []

        index = self.get_index()
        while not self.scanned:
            try:
                body.append(self.parse_declaration())
            except ParseError as exc:
                if mode == "repl":
                    raise

                errors.append(exc)
                self.synchronize()

        program = Program(body, index=index)
        return (program, errors) if mode == "file" else program

    def parse_declaration(self) -> Stmt:
        if self.match_next(TokenType.VAR):
            return self.parse_var_declaration()

        return self.parse_statement()

    def parse_var_declaration(self) -> VarDeclaration:
        index = self.get_index()
        name = self.consume(TokenType.IDENTIFIER)

        if not self.match_next(TokenType.EQUAL):
            return VarDeclaration(name, index=index)

        initializer = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        return VarDeclaration(name, initializer, index=index)

    def parse_statement(self) -> Stmt:
        if self.match_next(TokenType.LEFT_BRACE):
            return self.parse_block()

        if self.match_next(TokenType.PRINT):
            return self.parse_print_stmt()

        if self.match_next(TokenType.IF):
            return self.parse_if_stmt()

        if self.match_next(TokenType.WHILE):
            return self.parse_while_stmt()

        return self.parse_expr_stmt()

    def parse_block(self) -> Block:
        index = self.get_index()
        statements = self.parse_block_statements()
        self.consume(TokenType.RIGHT_BRACE)
        return Block(body=statements, index=index)

    def parse_block_statements(self) -> list[Stmt]:
        statements: list[Stmt] = []
        while not self.scanned and not self.peek_next(TokenType.RIGHT_BRACE):
            statements.append(self.parse_declaration())

        return statements

    def parse_print_stmt(self) -> Print:
        index = self.get_index()
        expression = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        return Print(expression, index=index)

    def parse_if_stmt(self) -> If:
        index = self.get_index()
        self.consume(TokenType.LEFT_PAREN)
        condition = self.parse_expression()
        self.consume(TokenType.RIGHT_PAREN)
        body = self.parse_declaration()

        if self.match_next(TokenType.ELSE):
            else_body = self.parse_declaration()
            return If(condition, body, else_body, index=index)

        return If(condition, body, index=index)

    def parse_while_stmt(self) -> While:
        index = self.get_index()
        self.consume(TokenType.LEFT_PAREN)
        condition = self.parse_expression()
        self.consume(TokenType.RIGHT_PAREN)
        body = self.parse_declaration()
        return While(condition, body, index=index)

    def parse_for_stmt(self) -> For:
        index = self.get_index()
        self.consume(TokenType.LEFT_PAREN)
        condition = self.parse_expression()
        self.consume(TokenType.RIGHT_PAREN)
        body = self.parse_declaration()
        return While(condition, body, index=index)

    def parse_expr_stmt(self) -> ExprStmt:
        expression = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        return ExprStmt(expression, index=expression.index)

    def parse_expression(self) -> Expr:
        return self.parse_assignment()

    def parse_assignment(self) -> Expr:
        expr = self.parse_equality()
        if self.match_next(TokenType.EQUAL):
            equals_token = self.previous()
            # Assume it to be assignment
            if not isinstance(expr, Variable):
                raise ParseError("Invalid assign target", equals_token)

            value = self.parse_assignment()
            return Assignment(expr.name, value, index=expr.index)

        # If it's not assignment, it's equality (or anything below)
        return expr

    def parse_equality(self) -> Expr:
        left = self.parse_comparison()

        while self.match_next(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL):
            operator = self.previous()
            right = self.parse_comparison()

            left = Binary(left, operator, right, index=left.index)

        return left

    def parse_comparison(self) -> Expr:
        left = self.parse_term()

        while self.match_next(
            TokenType.GREATER,
            TokenType.GREATER_EQUAL,
            TokenType.LESS,
            TokenType.LESS_EQUAL,
        ):
            operator = self.previous()
            right = self.parse_term()

            left = Binary(left, operator, right, index=left.index)

        return left

    def parse_term(self) -> Expr:
        left = self.parse_factor()

        while self.match_next(TokenType.PLUS, TokenType.MINUS):
            operator = self.previous()
            right = self.parse_factor()

            left = Binary(left, operator, right, index=left.index)

        return left

    def parse_factor(self) -> Expr:
        left = self.parse_unary()

        while self.match_next(TokenType.STAR, TokenType.SLASH):
            operator = self.previous()
            right = self.parse_unary()

            left = Binary(left, operator, right, index=left.index)

        return left

    def parse_unary(self) -> Expr:
        if self.match_next(TokenType.MINUS, TokenType.BANG):
            operator = self.previous()
            right = self.parse_unary()
            return Unary(operator, right, index=operator.index)

        return self.parse_primary()

    def parse_primary(self) -> Expr:
        if self.scanned:
            eof_token = self.get_token()
            raise ParseEOFError("Unexpected end of file while parsing", eof_token)

        if self.match_next(TokenType.STRING, TokenType.NUMBER):
            token = self.previous()
            return Literal(token.value, index=token.index)

        if self.match_next(TokenType.TRUE):
            return Literal(True, index=self.get_index())
        if self.match_next(TokenType.FALSE):
            return Literal(False, index=self.get_index())
        if self.match_next(TokenType.NIL):
            return Literal(None, index=self.get_index())

        if self.match_next(TokenType.IDENTIFIER):
            name = self.previous()
            return Variable(name, index=name.index)

        if self.match_next(TokenType.LEFT_PAREN):
            index = self.get_index()
            expression = self.parse_expression()
            self.consume(TokenType.RIGHT_PAREN)
            return Grouping(expression, index=index)

        token = self.get_token()
        raise ParseError(f"Unexpected token: {token.string!r}", token)

    def consume(self, expected_type: TokenType) -> Token:
        """Consumes one token. If it's not of the expected type, throws."""
        token = self.get_token()

        if token == EOF:
            raise ParseEOFError(
                f"Expected to find {expected_type.value!r}, found EOF",
                token,
            )

        if token.token_type != expected_type:
            raise ParseError(
                f"Expected to find {expected_type.value!r}, found {token.string!r}",
                token,
            )

        self.advance()
        return token


def main() -> None:
    source = " ".join(sys.argv[1:])
    tokens = Lexer(source).tokens

    parser = Parser(tokens)
    program = parser.parse()
    print(program)


if __name__ == "__main__":
    main()
