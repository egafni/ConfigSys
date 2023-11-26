import dataclasses
from importlib import import_module

import fsspec  # type: ignore[import]


def iter_items_dict_or_dataclass(x):
    """
    if x is a dict, iterates over key,val tuples
    if x is a dataclass, iterates over key,val tuples of its dataclass field names and values
    """
    if isinstance(x, dict):
        yield from x.items()
    if dataclasses.is_dataclass(x):
        yield from dataclasses.asdict(x).items()


def classproperty(func):
    """
    copied from https://stackoverflow.com/questions/5189699/how-to-make-a-class-property
    similar to @property decorator but works on an uninstantiated object"""
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)


class ClassPropertyDescriptor:
    """copied from https://stackoverflow.com/questions/5189699/how-to-make-a-class-property"""

    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self


def import_and_instantiate(import_path: str, *args, **kwargs):
    """
    :param import_path: path to a module
    :param *args: args to pass to the init
    :param kwargs: kwargs to pass to init

    >>> import_and_instantiate('datetime.timedelta', seconds=3600)
    datetime.timedelta(seconds=3600)
    """
    module_name, class_name = get_module_and_class_names(import_path)
    cls = getattr(import_module(module_name), class_name)
    return cls(*args, **kwargs)


def get_module_and_class_names(class_path: str) -> tuple[str, str]:
    """
    Return module name and class name from full class path
    >>> get_module_and_class_names("torch.optim.Adam")
    ('torch.optim', 'Adam')
    """
    split = class_path.split(".")
    class_name = split[-1]
    module_name = ".".join(split[:-1])
    return module_name, class_name
