from dataclasses import dataclass

import pytest
from dacite import DaciteError

from configsys.utils import REQUIRED, ConfigMixin, check_required


def test_required():
    with pytest.raises(DaciteError):
        # make sure we raise an exception if the REQUIRED default is set for any field
        check_required(dict(a=dict(b=dict(c=REQUIRED))))


def test_replace_fields():
    @dataclass
    class Thing(ConfigMixin):
        color: str

    @dataclass
    class Box(ConfigMixin):
        width: int
        height: int
        thing: Thing

    config = Box(width=10, height=5, thing=Thing(color="red"))
    config2 = config.copy()

    config.replace_fields({"width": 20, "thing.color": "orange"}, in_place=True)
    config2.width = 20
    config2.thing.color = "orange"

    assert config == config2
