from Library.Model.Method import DDPG
from Library.Model.Method.DDPG import *

from Library.Model.Method import TD3
from Library.Model.Method.TD3 import *

from Library.Model.Method import SAC
from Library.Model.Method.SAC import *

__all__ = [
    *DDPG.__all__,
    *TD3.__all__,
    *SAC.__all__
]