from dataclasses import dataclass, InitVar, field
@dataclass
class Base:
    db: InitVar[int] = field(kw_only=True, default=1)

@dataclass
class Child(Base):
    a: InitVar[int]
    def __post_init__(self, *args, **kwargs):
        print(f"args: {args}, kwargs: {kwargs}")

Child(2, db=3)
