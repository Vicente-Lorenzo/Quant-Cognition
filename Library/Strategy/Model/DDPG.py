from typing import Union
from Library.Parameter import Parameter

from Library.Engine import MachineAPI
from Library.Strategy import StrategyAPI

class DDPGStrategyAPI(StrategyAPI):

    def __init__(self,
                 money_management: Parameter,
                 risk_management: Parameter,
                 signal_management: Parameter):

        super().__init__(money_management, risk_management, signal_management)

    def risk_management(self) -> Union[MachineAPI, None]:
        return None

    def signal_management(self) -> Union[MachineAPI, None]:
        return None