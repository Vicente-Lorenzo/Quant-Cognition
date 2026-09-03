from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Union

class SplitAPI:

    @staticmethod
    def _purged_(train: tuple, purge: Union[int, None]) -> tuple:
        if not purge: return train
        start, stop = train
        trimmed = stop - timedelta(days=purge)
        return (start, trimmed) if trimmed > start else train

    @staticmethod
    def _embargoed_(train: tuple, previous: Union[tuple, None], embargo: Union[int, None]) -> tuple:
        if not embargo or previous is None: return train
        start, stop = train
        resumed = previous[1] + timedelta(days=embargo)
        return (resumed, stop) if start < resumed < stop else train

    @classmethod
    def _guarded_(cls, folds: list, purge: Union[int, None], embargo: Union[int, None], rolling: bool) -> list:
        if not purge and not embargo: return folds
        guarded, previous = [], None
        for train, validation in folds:
            window = cls._embargoed_(train, previous, embargo) if rolling else train
            window = cls._purged_(window, purge) if validation is not None else window
            guarded.append((window, validation))
            previous = validation or train
        return guarded

    @classmethod
    def walk_forward_folds(cls, start: datetime, stop: datetime, training: int, validation: int, testing: int,
                           rolling: bool, purge: Union[int, None] = None, embargo: Union[int, None] = None) -> tuple[list, Union[tuple, None]]:
        test = None
        inner_stop = stop
        if testing > 0:
            test_start = max(start, stop - relativedelta(months=testing))
            test = (test_start, stop)
            inner_stop = test_start
        folds = []
        if validation <= 0:
            folds.append(((start, inner_stop), None))
        elif training <= 0:
            split = max(start, inner_stop - relativedelta(months=validation))
            folds.append(((start, split), (split, inner_stop)))
        else:
            cursor = start
            while True:
                train_start = cursor if rolling else start
                train_stop = cursor + relativedelta(months=training)
                validation_stop = train_stop + relativedelta(months=validation)
                if validation_stop > inner_stop or train_stop >= inner_stop: break
                folds.append(((train_start, train_stop), (train_stop, validation_stop)))
                cursor = cursor + relativedelta(months=validation)
            if not folds: folds.append(((start, inner_stop), None))
        return cls._guarded_(folds, purge, embargo, rolling), test

__all__ = ["SplitAPI"]