from typing import Union
from math import floor

from Library.Parameters import Parameters

from Library.Classes import *
from Library.Manager import PositionAPI, StatisticsAPI

class ManagerAPI:

    def __init__(self, manager_management: Parameters):
        self.ManagerManagement = manager_management
        self.Account: Union[Account, None] = None
        self.Security: Union[Security, None] = None
        self.Positions: PositionAPI = PositionAPI()
        self.Statistics: StatisticsAPI = StatisticsAPI()

    def init_security(self, security: Security):
        self.Security = security

    def update_account(self, account: Account):
        self.Account = account

    def update_security(self, bar: Bar):
        self.Security.SpotPrice = bar.ClosePrice

    def normalize_volume(self, volume: float, apply=floor) -> float:
        normalized = apply(volume / self.Security.VolumeInUnitsStep) * self.Security.VolumeInUnitsStep
        return max(self.Security.VolumeInUnitsMin, min(normalized, self.Security.VolumeInUnitsMax))

    def volume_by_amount(self, amount: float, sl_pips: float) -> float:
        return amount / (sl_pips * self.Security.PipValue) * self.Security.LotSize

    def volume_by_risk(self, risk_percentage: float, sl_pips: float):
        amount = self.Account.Balance * risk_percentage / 100
        volume = self.volume_by_amount(amount, sl_pips)
        return self.normalize_volume(volume)

    def data(self):
        return self.Positions.data()

    def __repr__(self) -> str:
        return repr(self.data())