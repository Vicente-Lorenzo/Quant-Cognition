from datetime import datetime
from typing import Union

from dateutil.relativedelta import relativedelta

class SplitAPI:

    @staticmethod
    def walk_forward_folds(start: datetime, stop: datetime, training: int, validation: int, testing: int, rolling: bool) -> tuple[list, Union[tuple, None]]:
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
        return folds, test