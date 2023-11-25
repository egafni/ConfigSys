from dataclasses import dataclass

import pytest
from configsys import example
from configsys.config import REQUIRED, ConfigMixin, check_required
from dacite import DaciteError


def test_required():
    with pytest.raises(DaciteError):
        # make sure we raise an exception if the REQUIRED default is set for any field
        check_required(dict(a=dict(b=dict(c=REQUIRED))))


def test_replace_fields(tmpdir):
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

    # check saving
    config.to_yaml_file(f'{tmpdir}/config.yaml')
    config3 = Box.from_yaml_file(f'{tmpdir}/config.yaml')
    assert config == config3


def test_example(tmpdir):
    example.main(tmpdir)
