from Redy.Magic.Pattern import Pattern
from GraphEngine.tsl.type.system import TSLType, Cell, List, StructTypeSpec, ListTypeSpec, \
    PrimitiveTypeSpec, Struct
import struct
import ast
import copy
import typing
from rbnf._py_tools.unparse import Unparser

struct_pack = struct.pack


def int_to_bytes(value, byte_num=4):
    length = ast.Call(
        func=ast.Name(id='len', ctx=ast.Load()), keywords=[], args=[value])
    attr = ast.Attribute(value=length, attr='to_bytes', ctx=ast.Load())
    return ast.Call(
        func=attr,
        keywords=[],
        args=[ast.Num(n=byte_num), ast.Str(s="little")])


def float_to_bytes(value):
    return ast.Call(
        func=ast.Name(id='struct_pack', ctx=ast.Load()),
        keywords=[],
        args=[ast.Str(s='>f'), value])

def double_to_bytes(value):
    return ast.Call(func=ast.Name(id='struct_pack', ctx=ast.Load()), keywords=[], args=[ast.Str(s='>d'), value])


def str_to_bytes(value):
    return ast.Call(func=ast.Attribute(value=value, attr='encode', ctx=ast.Load()), keywords=[], args=[])


def make_get_bytes(spec, depth=0) -> typing.Callable:

    def call(node: ast.AST):
        identifier = f'obj_{depth}'
        value = node

        if isinstance(spec, PrimitiveTypeSpec):
            if spec.type_code == 'I8':
                return ast.Yield(value=int_to_bytes(value, 1))
            if spec.type_code == 'I16':
                return ast.Yield(value=int_to_bytes(value, 2))
            if spec.type_code == 'I32':
                return ast.Yield(value=int_to_bytes(value, 4))
            if spec.type_code == 'I64':
                return ast.Yield(value=int_to_bytes(value, 8))

            if spec.type_code == 'STRING':
                return ast.Yield(value=str_to_bytes(value))

            if spec.type_code == 'U8STRING':
                return ast.Yield(value=value)

            if spec.type_code == 'F32':
                return ast.Yield(value=float_to_bytes(value))

            if spec.type_code == 'F64':
                return ast.Yield(value=double_to_bytes(value))

            raise TypeError
        value = ast.Name(id=identifier, ctx=ast.Load())
        alias = ast.Assign(
            targets=[ast.Name(id=identifier, ctx=ast.Store())], value=node)


        if isinstance(spec, StructTypeSpec):
            ret = [alias]
            for name, field_spec in spec.field_types.items():
                sub = make_get_bytes(field_spec, depth + 1)(ast.Subscript(
                    value=value,
                    slice=ast.Index(value=ast.Str(name)),
                    ctx=ast.Load()))
                if isinstance(sub, list):
                    ret.extend(sub)
                else:
                    ret.append(sub)

            return ret


        else:
            assert isinstance(spec, ListTypeSpec)
            head_bytes = int_to_bytes(value)
            iter_var = ast.Name(id=f'each{depth}', ctx=ast.Store())
            return [
                ast.Yield(value=head_bytes),
                ast.For(
                    target=iter_var,
                    iter=value,
                    body=make_get_bytes(spec.elem_type, depth + 1))
            ]

    return call

class S(Struct):
    b: int

class C(Cell):
    a: int
    s: S

    pass


def make_fast_to_bytes_function(ty):
    print(ty, ty.__mro__)
    assert issubclass(ty, (Struct, List))
    f = make_get_bytes(ty.get_spec())
    bind_struct_pack = ast.Assign(
        targets=[ast.Name(id="struct_pack", ctx=ast.Store())],
        value=ast.Attribute(
            value=ast.Name(id='struct', ctx=ast.Load()),
            attr='pack',
            ctx=ast.Load()))

    node = ast.FunctionDef(
        name='f',
        args=ast.arguments(
            args=[ast.arg(arg='obj', annotation=None)],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[]),
        decorator_list=[],
        returns=None,
        body=[bind_struct_pack, *f(ast.Name(id='obj', ctx=ast.Load()))])
    ast.fix_missing_locations(node)

    import astpretty
    astpretty.pprint(node)
    Unparser(node)

    return node


f = make_fast_to_bytes_function(C)
