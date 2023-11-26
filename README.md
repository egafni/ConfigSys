# ConfigSys

Very simple yet powerful configuration system for machine learning projects.  The whole thing is
around 170 lines of code, give it a look!

Provides a simple way to use nested dataclasses to specify an arbitrary complex configuration.  Configs can be
easily serialized to and from yaml files and back to nested dataclasses.

see configsys/example.py

For a more complex example see [this](http://github.com/egafni/ai) repo.

# Core Beliefs

Specifying configs in python is **way** better than raw yaml text files.
* You get all the help of the IDE (e.g. autocomplete, type checking, refactoring, etc.)
* You can use python logic (for loops, string replacement, functions, itertools, etc.) 
  to decide your hyper-parameters and experiments.

The CLI is a terrible way to specify hyper-parameters or complex configs
* CLI configuration is basically an attempt at taking a 1 line string and serializing it into a python nested datastructure
* It is much easier to just create a python file which configures and runs (or launches) your jobs.

# Install
```bash

pip install configsys

```
# Example Usage
```python
from dataclasses import dataclass

from configsys.config import ConfigMixin

# We recommend using kw_only=True to make sure Configs are specified explicitly
class ImageDataLoader:
    @dataclass(kw_only=True)
    class Config(ConfigMixin):
        _target_ = "configsys.example.ImageDataLoader"
        batch_size: int
        shuffle: bool

    def __init__(self, config: Config):
        self.config = config

    def get_data(self):
        return dict(x=[2, 3], y=[4, 5])


class TextDataLoader:
    @dataclass(kw_only=True)
    class Config(ConfigMixin):
        _target_ = "configsys.example.TextDataLoader"
        batch_size: int
        shuffle: bool

    def __init__(self, config: Config):
        self.config = config

    def get_data(self, x):
        return dict(x=['hello', 'world'])


class MLP:
    @dataclass(kw_only=True)
    class Config(ConfigMixin):
        _target_ = "configsys.example.MLP"
        n_layers: int
        n_hidden: int

    def __init__(self, config: Config):
        self.config = config

    def forward(self, x):
        return x


class Transformer:
    @dataclass(kw_only=True)
    class Config(ConfigMixin):
        _target_ = "configsys.example.Transformer"
        n_heads: int

    def __init__(self, config: Config):
        self.config = config

    def forward(self, x):
        return x


# Configs do not necessarily have to be an attribute of their target class
# This is usually the case when the target is class that you did not write
@dataclass(kw_only=True)
class TrainerConfig(ConfigMixin):
    _target_ = "configsys.example.Trainer"
    dataloader: ImageDataLoader.Config | TextDataLoader.Config
    model: MLP.Config | Transformer.Config
    learning_rate: float
    steps: int


class Trainer:
    def __init__(self, config: TrainerConfig):
        self.config = config

    def train(self):
        print("{self} training...")
        print(self.config.learning_rate)
        print(self.config.steps)


def main(outdir):
    for model_config in [MLP.Config(n_layers=3, n_hidden=128),
                         Transformer.Config(n_heads=6)]:
        config = TrainerConfig(
            dataloader=ImageDataLoader.Config(batch_size=32, shuffle=True),
            model=model_config,
            learning_rate=0.1,
            steps=100,
        )
        model = config.model.instantiate_target()
        dataloader = config.dataloader.instantiate_target()
        trainer = config.instantiate_target()  # equivalent to trainer = Trainer(config=trainer_config)
        trainer.train()

        config.to_yaml_file(f"{outdir}/trainer_config.yaml")

        trainer_config2 = TrainerConfig.from_yaml_file(f"{outdir}/trainer_config.yaml")
        assert config == trainer_config2



```
