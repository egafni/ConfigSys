# ConfigSys

Extremely simple and powerful configuration system for machine learning systems.  
Provides a simple way to use nested dataclasses to specify an arbitrary complex configuration.  Configs can be
easily serialized to and from yaml files, although we highly recommend specifying configs in **python** rather than yaml 
since you get all the benefits of an IDE (e.g. autocomplete, type checking, etc.).

see configsys/example.py

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


if __name__ == '__main__':
    main()


```
