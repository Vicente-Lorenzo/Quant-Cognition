from typing import Union, ClassVar
from dataclasses import dataclass

from Library.Database.Dataclass import DataclassAPI
from Library.Market.Price import PriceAPI
from Library.Market.Tick import TickAPI

@dataclass
class PointAPI(DataclassAPI):

    _flatten_: ClassVar[tuple[str, ...]] = ("AskTick", "BidTick")

    AskTick: Union[TickAPI, None] = None
    BidTick: Union[TickAPI, None] = None

    @property
    def Ask(self) -> Union[PriceAPI, None]:
        return self.AskTick.Ask if self.AskTick is not None else None

    @property
    def Bid(self) -> Union[PriceAPI, None]:
        return self.BidTick.Bid if self.BidTick is not None else None