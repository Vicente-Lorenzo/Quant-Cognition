from typing import Union

from Library.Engine import MachineAPI
from Library.Parameters import Parameters
from Library.Strategy.Strategy import StrategyAPI

class DownloadStrategyAPI(StrategyAPI):

    def __init__(self,
                 money_management: Parameters,
                 risk_management: Parameters,
                 signal_management: Parameters) -> None:
        super().__init__(money_management, risk_management, signal_management)

    def risk_management(self) -> Union[MachineAPI, None]:
        return None

    def signal_management(self) -> Union[MachineAPI, None]:
        return None