import dataclasses
import os
from copy import deepcopy
from dataclasses import Field, dataclass, fields
from importlib import import_module
from inspect import isclass
from typing import Any

import dacite
import fsspec  # type: ignore[import]
import yaml
from dacite import DaciteError


class _REQUIRED:
    """
    Dataclass inheritance is horrible due to the requirement that defaults follow non-defaults.  This is a hacky way
    around that until python3.10 when we can set @dataclass(kw_only=True),
    """


REQUIRED: Any = _REQUIRED


def iter_items_dict_or_dataclass(x):
    """
    if x is a dict, iterates over key,val tuples
    if x is a dataclass, iterates over key,val tuples of its dataclass field names and values
    """
    if isinstance(x, dict):
        yield from x.items()
    if dataclasses.is_dataclass(x):
        yield from dataclasses.asdict(x).items()


def check_required(obj, path=""):
    """
    check all REQUIRED fields were set
    :param obj: either a (nested) dataclass or a (nested) dict
    """

    if isinstance(obj, dict) or dataclasses.is_dataclass(obj):
        for k, v in iter_items_dict_or_dataclass(obj):
            check_required(v, path=os.path.join(path, k))
    elif obj is REQUIRED:
        raise DaciteError(f"{path} is a required field")


@dataclass
class ConfigMixin:
    """
    A mixin for a dataclass used to create composable Configuration objects.
    """

    def __post_init__(self):
        check_required(self)

        for field in self.fields:
            if field.name == "unique_config_id":
                # require that unique_config_id is set to the default value so that we're instantiating
                # the correct class.  This is required by dacite's UnionType[] support, which continues trying each
                # type after a failure
                unique_config_id = getattr(self, field.name)
                if unique_config_id != field.default:
                    raise DaciteError(
                        f"unique_config_id `{unique_config_id}`" f" should be {field.default} to instantiate this class"
                    )

            if "choices" in field.metadata:
                val = getattr(self, field.name)
                if val not in field.metadata["choices"]:
                    raise ValueError(f'{field.name} is invalid, it must be in {field.metadata["choices"]}')

    def get_target(self):
        """returns the _target_ class of this config"""
        assert hasattr(self, "_target_"), "_target_ attribute was not specified for this config"
        module_name, class_name = get_module_and_class_names(self._target_)  # type: ignore
        return getattr(import_module(module_name), class_name)

    @classproperty
    def fields(cls) -> tuple[Field, ...]:
        return fields(cls)

    @classproperty
    def field_names(cls) -> list[str]:
        return [f.name for f in cls.fields]

    @classmethod
    def get_name_to_field(cls):
        return dict(zip(cls.field_names, cls.fields))

    def __repr__(self):
        keys = ",".join(self.field_names)
        return f"{self.__class__.__name__}({keys})"

    def to_dict(self):
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data):
        # fixme we should enable strict_unions_match=True to make sure only one of the UnionType matches
        obj = dacite.from_dict(cls, data, dacite.Config(strict=True))
        check_required(obj)
        return obj

    def __iter__(self):
        for field_name in self.field_names:
            yield getattr(self, field_name)

    @classmethod
    def from_yaml_file(cls, path):
        with fsspec.open(path) as fp:
            s = fp.read().decode()

        return cls.from_yaml(s)

    @classmethod
    def from_yaml(cls, yaml_string):
        return cls.from_dict(yaml.load(yaml_string, Loader=yaml.Loader))

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict())  # type: ignore[no-any-return]

    def to_yaml_file(self, path):
        with fsspec.open(path, "w") as fp:
            fp.write(self.to_yaml())

    # commented because pycharm treated it as an abstract method and added a lot of warnings
    # def interpolated(self):
    # raise NotImplementedError(
    #     "interpolated not implemented, normally this would "
    #     "allow you to set values as references to other config variables"
    # )

    def instantiate_target(self, *args, **kwargs):
        """
        Instantiates the target class this config belongs to
        The target class must be specified in self._target_
        """
        assert hasattr(self, "_target_"), "_target_ attribute was not specified for this config"
        return import_and_instantiate(self._target_, config=self, *args, **kwargs)  # type: ignore

    def i(self, *args, **kwargs):
        """alias to instantiate_target"""
        return self.instantiate_target(*args, **kwargs)

    def replace_fields(self, new_fields: dict[str, Any], in_place):
        root = self if in_place else self.copy()

        for full_name, value in new_fields.items():
            names = full_name.split(".")
            obj = root
            for name in names[:-1]:
                obj = getattr(obj, name)
            if isinstance(obj, dict):
                obj[names[-1]] = value
            elif dataclasses.is_dataclass(obj):
                setattr(obj, names[-1], value)
            else:
                raise NameError(f"No field {full_name} in the config")

        return root

    def copy(self):
        return deepcopy(self)


def are_configs_equal(first: dict, second: dict) -> bool:
    return {key: value for key, value in first.items() if key not in ["name", "unique_id"]} == {
        key: value for key, value in second.items() if key not in ["name", "unique_id"]
    }


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


def classproperty(func):
    """
    copied from https://stackoverflow.com/questions/5189699/how-to-make-a-class-property
    similar to @property decorator but works on an uninstantiated object"""
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)


def get_subclasses_from_object_dict(class_: type, object_dict: dict) -> dict[str, type]:
    """
    Returns all of the subclasses of class_ that are inside object_dict, which is usually passed in as the
    globals() of the caller.
    Useful for getting all of the subclasses of a class that are defined in a module.
    :param class_: A class
    :param object_dict: an object dictionary (for ex the output of globals())
    :return: dict of {"class_name": class, ...} where class is as subtype of class_
    """
    return {
        var_name: variable
        for var_name, variable in object_dict.items()
        if isclass(variable) and issubclass(variable, class_) and var_name != class_.__name__
    }


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
