from __future__ import annotations

from typing import Union
from dataclasses import dataclass, field

from Library.Database.Dataclass import DataclassAPI
from Library.Market.Price import Direction

@dataclass(slots=True, kw_only=True)
class PnLAPI(DataclassAPI):

    PnL: float = field(init=True, repr=True)
    Reference: Union[float, None] = field(default=None, init=True, repr=True)
    Duration: Union[float, None] = field(default=None, init=True, repr=True)

    @property
    def UID(self) -> float:
        return self.PnL

    @property
    def LogPnL(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_log_value
        return calculate_log_value(self.PnL)

    @property
    def Direction(self) -> Direction:
        from Library.Portfolio.Statistic import calculate_direction
        return calculate_direction(self.PnL)

    @property
    def Return(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_pnl_return
        return calculate_pnl_return(self.PnL, self.Reference)

    @property
    def LogReturn(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_log_return
        return calculate_log_return(self.Return)

    @property
    def Percentage(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_percentage
        return calculate_percentage(self.Return)

    @property
    def LogPercentage(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_log_percentage
        return calculate_log_percentage(self.LogReturn)

    @property
    def AnnualizedReturn(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_annualized_return
        ret = self.Return
        if ret is None or not self.Duration or self.Duration <= 0.0: return None
        return calculate_annualized_return(ret, self.Duration)

    @property
    def AnnualizedLogReturn(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_annualized_log_return
        log_ret = self.LogReturn
        if log_ret is None or not self.Duration or self.Duration <= 0.0: return None
        return calculate_annualized_log_return(log_ret, self.Duration)

    @property
    def AnnualizedPercentage(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_percentage
        return calculate_percentage(self.AnnualizedReturn)

    @property
    def AnnualizedLogPercentage(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_log_percentage
        return calculate_log_percentage(self.AnnualizedLogReturn)