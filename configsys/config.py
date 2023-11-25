import dataclasses
import os
from copy import deepcopy
from dataclasses import Field, dataclass, fields
from importlib import import_module
from typing import Any

import dacite
import fsspec  # type: ignore[import]
import yaml
from dacite import DaciteError

from configsys.utils import classproperty, get_module_and_class_names, import_and_instantiate


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
