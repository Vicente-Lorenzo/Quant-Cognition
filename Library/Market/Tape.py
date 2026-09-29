from __future__ import annotations

from typing import Union
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from Library.Database.Dataframe import np, pl
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Database.Query import QueryAPI
from Library.Market.Tick import TickAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Datetime import datetime_to_epoch, epoch_to_datetime, utc_now
from Library.Utility.Memory import BlockAPI
from Library.Utility.Typing import MISSING, Missing

@dataclass(frozen=True)
class TapeAPI:

    Security: int
    Stamps: np.ndarray
    Asks: np.ndarray
    Bids: np.ndarray
    Volumes: np.ndarray
    Bounds: Union[tuple[int, int], None] = None
    Memory: Union[BlockAPI, None] = field(default=None, repr=False, compare=False)

    @staticmethod
    def _table_() -> str:
        return '"Market"."Tick"'

    @staticmethod
    def _interval_() -> int:
        return 31 * 86_400_000

    @staticmethod
    def _row_() -> np.dtype:
        return np.dtype([("UID", ">i8"), ("Ask", ">i8"), ("Bid", ">i8")])

    @staticmethod
    def _size_() -> np.dtype:
        return np.dtype([("UID", ">i8"), ("Volume", ">f8")])

    @staticmethod
    def _bounds_(security: int) -> tuple[int, int]:
        return security << TickAPI.bits(), ((security + 1) << TickAPI.bits()) - 1

    @staticmethod
    def _chunks_(low: int, high: int, size: int = 4_000_000) -> list[tuple[int, int]]:
        return [(start, min(start + size, high)) for start in range(low, high, size)]

    @staticmethod
    def _moments_(stamps: np.ndarray) -> pl.Series:
        return pl.Series(stamps).cast(pl.Datetime("ms")).cast(pl.Datetime("us"))

    @staticmethod
    def _length_(timeframe: TimeframeAPI) -> timedelta:
        if timeframe.IsTick: raise ValueError(f"Timeframe {timeframe.UID}: Failed · Due to tick bars having no duration")
        return timedelta(seconds=timeframe.Seconds)

    @classmethod
    def _spans_(cls, low: int, high: int) -> list[tuple[int, int]]:
        if high < low: return []
        interval = cls._interval_()
        starts = [low, *range((low // interval + 1) * interval, high + 1, interval)]
        return list(zip(starts, [*(start - 1 for start in starts[1:]), high]))

    @staticmethod
    def _zone_(first: int, last: int, zone: str) -> tuple[np.ndarray, np.ndarray]:
        step = 900_000
        grid = np.arange(first // step * step, last + step, step, dtype=np.int64)
        offsets = pl.Series(grid).cast(pl.Datetime("ms")).dt.replace_time_zone("UTC").dt.convert_time_zone(zone).dt.replace_time_zone(None).cast(pl.Int64).to_numpy() - grid
        change = np.flatnonzero(np.diff(offsets)) + 1
        return np.concatenate((grid[:1], grid[change])), np.concatenate((offsets[:1], offsets[change]))

    @staticmethod
    def _bucket_(session: np.ndarray, timeframe: TimeframeAPI) -> np.ndarray:
        value, day = timeframe.Value or 1, 86_400_000
        match timeframe.Unit:
            case "MN": return session.astype("datetime64[ms]").astype("datetime64[M]").astype(np.int64) // value
            case "Y": return session.astype("datetime64[ms]").astype("datetime64[Y]").astype(np.int64) // value
            case "W": return (session - 4 * day) // (value * 7 * day)
            case _: return session // round(timeframe.Seconds * 1000)

    @staticmethod
    def _origins_(keys: np.ndarray, timeframe: TimeframeAPI) -> np.ndarray:
        value, day = timeframe.Value or 1, 86_400_000
        match timeframe.Unit:
            case "MN": return (keys * value).astype("datetime64[M]").astype("datetime64[ms]").astype(np.int64)
            case "Y": return (keys * value).astype("datetime64[Y]").astype("datetime64[ms]").astype(np.int64)
            case "W": return keys * value * 7 * day + 4 * day
            case _: return keys * round(timeframe.Seconds * 1000)

    @staticmethod
    def _first_(values: np.ndarray, reduce: np.ufunc, starts: np.ndarray, lengths: np.ndarray) -> np.ndarray:
        if lengths.sum() >= 1024 * lengths.size:
            pick = np.argmax if reduce is np.maximum else np.argmin
            return np.fromiter((start + pick(values[start:start + length]) for start, length in zip(starts.tolist(), lengths.tolist())), dtype=np.int64, count=starts.size)
        hits = np.flatnonzero(values == np.repeat(reduce.reduceat(values, starts), lengths))
        return hits[np.searchsorted(hits, starts)]

    @classmethod
    def _view_(cls, security: int, memory: BlockAPI, size: int, bounds: tuple[int, int], writeable: bool) -> TapeAPI:
        stamps = np.frombuffer(memory.buf, dtype=np.int64, count=size, offset=0)
        asks = np.frombuffer(memory.buf, dtype=np.float64, count=size, offset=8 * size)
        bids = np.frombuffer(memory.buf, dtype=np.float64, count=size, offset=16 * size)
        volumes = np.frombuffer(memory.buf, dtype=np.float64, count=size, offset=24 * size)
        stamps.flags.writeable = asks.flags.writeable = bids.flags.writeable = volumes.flags.writeable = writeable
        return cls(Security=security, Stamps=stamps, Asks=asks, Bids=bids, Volumes=volumes, Bounds=bounds, Memory=memory)

    @classmethod
    def _allocate_(cls, security: int, size: int, bounds: tuple[int, int], shared: bool) -> TapeAPI:
        if not shared or not size: return cls(Security=security, Stamps=np.empty(size, dtype=np.int64), Asks=np.empty(size), Bids=np.empty(size), Volumes=np.empty(size), Bounds=bounds)
        return cls._view_(security, BlockAPI(create=True, size=32 * size), size, bounds, True)

    @classmethod
    def _part_(cls, db: PostgresDatabaseAPI, low: int, high: int) -> tuple[np.ndarray, np.ndarray]:
        row = db.binary(QueryAPI(f'''SELECT STRING_AGG(INT8SEND("UID") || INT8SEND("Ask") || INT8SEND("Bid"), CAST('' AS BYTEA) ORDER BY "UID") AS "Rows",
            STRING_AGG(INT8SEND("UID") || FLOAT8SEND("Volume"), CAST('' AS BYTEA) ORDER BY "UID") FILTER (WHERE "Volume" IS NOT NULL) AS "Sizes"
            FROM {cls._table_()} WHERE "UID" BETWEEN :low: AND :high:'''), low=low, high=high)
        rows = np.frombuffer(row[0], dtype=cls._row_()) if row and row[0] else np.empty(0, dtype=cls._row_())
        sizes = np.frombuffer(row[1], dtype=cls._size_()) if row and row[1] else np.empty(0, dtype=cls._size_())
        return rows, sizes

    @classmethod
    def _parts_(cls, db: PostgresDatabaseAPI, spans: list, workers: int) -> list:
        if workers <= 1 or len(spans) <= 1: return [cls._part_(db, *span) for span in spans]
        count = min(workers, len(spans))
        def work(group: list) -> list:
            with db.sibling() as sibling: return [(span, cls._part_(sibling, *span)) for span in group]
        with ThreadPoolExecutor(max_workers=count) as pool: results = [item for items in pool.map(work, [spans[index::count] for index in range(count)]) for item in items]
        return [part for _, part in sorted(results, key=lambda item: item[0][0])]

    @classmethod
    def _previous_(cls, db: PostgresDatabaseAPI, security: int, low: int) -> Union[tuple, None]:
        floor, _ = cls._bounds_(security)
        for bottom in dict.fromkeys((max(floor, low - 3_600_000), floor)):
            frame = db.executeone(QueryAPI(f'SELECT "Ask", "Bid" FROM {cls._table_()} WHERE "UID" < :low: AND "UID" >= :floor: ORDER BY "UID" DESC LIMIT 1'), low=low, floor=bottom).fetchall(legacy=False)
            if frame.height: return frame.row(0)
        return None

    def _decode_(self, part: tuple, offset: int, lead: Union[tuple, None]) -> None:
        rows, sizes = part
        stop, asks, bids = offset + rows.size, rows["Ask"], rows["Bid"]
        np.bitwise_and(rows["UID"], (1 << TickAPI.bits()) - 1, out=self.Stamps[offset:stop])
        np.divide(asks, 100_000.0, out=self.Asks[offset:stop])
        np.divide(bids, 100_000.0, out=self.Bids[offset:stop])
        moved = self.Volumes[offset:stop]
        moved[1:] = (asks[1:] != asks[:-1]).astype(np.float64) + (bids[1:] != bids[:-1])
        moved[0] = 2.0 if lead is None else float(lead[0] != asks[0]) + float(lead[1] != bids[0])
        if sizes.size: moved[np.searchsorted(rows["UID"], sizes["UID"])] = sizes["Volume"]

    def _starts_(self, pool: ThreadPoolExecutor, edges: np.ndarray, shifts: np.ndarray, timeframe: TimeframeAPI) -> tuple[np.ndarray, np.ndarray]:
        bounds = np.concatenate(([0], np.searchsorted(self.Stamps, edges[1:], side="left"), [self.Stamps.size]))
        pieces = [(low, high, shifts[index]) for index in range(bounds.size - 1) for low, high in self._chunks_(int(bounds[index]), int(bounds[index + 1]))]
        def work(piece: tuple) -> tuple:
            low, high, shift = piece
            keys = self._bucket_(self.Stamps[low:high] + shift, timeframe)
            inner = np.flatnonzero(keys[1:] != keys[:-1]) + 1
            return low + inner, keys[inner], keys[0], keys[-1]
        starts, heads, last = [], [], None
        for (low, _, _), (inner, keys, first, final) in zip(pieces, pool.map(work, pieces)):
            if last is None or first != last:
                starts.append(np.array([low], dtype=np.int64))
                heads.append(np.array([first], dtype=np.int64))
            starts.append(inner)
            heads.append(keys)
            last = final
        return np.concatenate(starts), np.concatenate(heads)

    def _extremes_(self, pool: ThreadPoolExecutor, starts: np.ndarray) -> dict:
        count, size = starts.size, self.Stamps.size
        columns = {name: np.empty(count, dtype=np.int64) for name in ("HighAsk", "HighBid", "HighMid", "LowAsk", "LowBid", "LowMid")}
        columns["Volume"] = np.empty(count)
        bounds = np.linspace(0, count, min(count, 64) + 1).astype(np.int64)
        def work(index: int) -> None:
            first, last = int(bounds[index]), int(bounds[index + 1])
            if first == last: return
            low, high = int(starts[first]), int(starts[last]) if last < count else size
            local = starts[first:last] - low
            lengths = np.diff(np.append(local, high - low))
            asks, bids = self.Asks[low:high], self.Bids[low:high]
            mids = asks + bids
            for name, values, reduce in (("HighAsk", asks, np.maximum), ("HighBid", bids, np.maximum), ("HighMid", mids, np.maximum), ("LowAsk", asks, np.minimum), ("LowBid", bids, np.minimum), ("LowMid", mids, np.minimum)):
                columns[name][first:last] = self._first_(values, reduce, local, lengths) + low
            columns["Volume"][first:last] = np.add.reduceat(self.Volumes[low:high], local)
        list(pool.map(work, range(bounds.size - 1)))
        return columns

    def _ticks_(self, index: np.ndarray, base: Union[tuple, None, Missing], quote: Union[tuple, None, Missing]) -> dict:
        stamps = self.Stamps[index]
        columns = {
            "UID": (self.Security << TickAPI.bits()) | stamps,
            "Volume": self.Volumes[index],
            "Security": np.full(index.size, self.Security, dtype=np.int64),
            "Timestamp": self._moments_(stamps),
            "Ask": self.Asks[index],
            "Bid": self.Bids[index]
        }
        for side, source in (("Base", base), ("Quote", quote)):
            if source is MISSING:
                columns[f"Ask{side}Conversion"] = columns[f"Bid{side}Conversion"] = pl.repeat(None, index.size, dtype=pl.Float64, eager=True)
            else:
                columns[f"Ask{side}Conversion"], columns[f"Bid{side}Conversion"] = self.rates(stamps, source)
        return columns

    @classmethod
    def empty(cls, security: int) -> TapeAPI:
        return cls(Security=security, Stamps=np.empty(0, dtype=np.int64), Asks=np.empty(0), Bids=np.empty(0), Volumes=np.empty(0))

    @classmethod
    def create(cls, db: PostgresDatabaseAPI) -> None:
        table = cls._table_()
        db.executeone(QueryAPI("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        db.executeone(QueryAPI('CREATE SCHEMA IF NOT EXISTS "Market"'))
        db.executeone(QueryAPI(f'''CREATE TABLE IF NOT EXISTS {table} ("UID" BIGINT NOT NULL, "Security" INTEGER NOT NULL REFERENCES {SecurityAPI.reference()},
            "Ask" BIGINT NOT NULL, "Bid" BIGINT NOT NULL, "Volume" DOUBLE PRECISION, "UpdatedAt" TIMESTAMPTZ, "UpdatedBy" VARCHAR, PRIMARY KEY ("UID"))'''))
        db.executeone(QueryAPI(f"SELECT create_hypertable('{table}', by_range('UID', {cls._interval_()}), if_not_exists => TRUE)"))
        compressed = db.executeone(QueryAPI("SELECT compression_enabled FROM timescaledb_information.hypertables WHERE hypertable_schema = 'Market' AND hypertable_name = 'Tick'")).fetchall(legacy=False)
        if not compressed.height or not compressed.item():
            db.executeone(QueryAPI(f'''ALTER TABLE {table} SET (timescaledb.compress, timescaledb.compress_segmentby = '"Security"', timescaledb.compress_orderby = '"UID"')'''))
        db.executeone(QueryAPI(f'ALTER TABLE {table} ALTER COLUMN "UID" SET STATISTICS 1000, ALTER COLUMN "Security" SET STATISTICS 1000'))

    @staticmethod
    def merge(asks: pl.DataFrame, bids: pl.DataFrame, carry: Union[tuple, None] = None) -> pl.DataFrame:
        stamp = str(TickAPI.ID.Timestamp)
        def side(frame: pl.DataFrame, column: str, other: str) -> pl.DataFrame:
            return frame.select(pl.col(stamp).dt.epoch("ms").alias("Stamp"), (pl.col(column) * 100_000).round().cast(pl.Int64).alias(column), pl.lit(None, dtype=pl.Int64).alias(other)).select("Stamp", "Ask", "Bid")
        merged = pl.concat([side(asks, "Ask", "Bid"), side(bids, "Bid", "Ask")]).sort("Stamp", maintain_order=True)
        merged = merged.group_by("Stamp", maintain_order=True).agg(pl.col("Ask").drop_nulls().last(), pl.col("Bid").drop_nulls().last())
        merged = merged.with_columns(pl.col("Ask").forward_fill(), pl.col("Bid").forward_fill())
        if carry is not None: merged = merged.with_columns(pl.col("Ask").fill_null(int(carry[0])), pl.col("Bid").fill_null(int(carry[1])))
        return merged.drop_nulls()

    @classmethod
    def previous(cls, db: PostgresDatabaseAPI, security: int, moment: datetime) -> Union[tuple, None]:
        return cls._previous_(db, security, TickAPI.encode(security, moment))

    @classmethod
    def _rows_(cls, security: int, frame: pl.DataFrame, by: str) -> pl.DataFrame:
        return frame.select((pl.col("Stamp") + (security << TickAPI.bits())).alias("UID"), pl.lit(security, dtype=pl.Int32).alias("Security"), "Ask", "Bid",
                            pl.lit(f"{utc_now():%Y-%m-%d %H:%M:%S.%f}+00:00").alias("UpdatedAt"), pl.lit(by).alias("UpdatedBy"))

    @staticmethod
    def _covering_(db: PostgresDatabaseAPI, low: int, high: int) -> list[str]:
        frame = db.executeone(QueryAPI("""SELECT QUOTE_IDENT(chunk_schema) || '.' || QUOTE_IDENT(chunk_name) AS "Chunk" FROM timescaledb_information.chunks WHERE hypertable_schema = 'Market' AND hypertable_name = 'Tick'
            AND range_start_integer <= :high: AND range_end_integer > :low:"""), low=low, high=high).fetchall(legacy=False)
        return frame["Chunk"].to_list() if frame.height else []

    @classmethod
    def write(cls, db: PostgresDatabaseAPI, security: int, frame: pl.DataFrame, start: datetime, stop: datetime, by: str) -> int:
        low, high = datetime_to_epoch(start), datetime_to_epoch(stop)
        frame = frame.filter((pl.col("Stamp") >= low) & (pl.col("Stamp") < high))
        first, last = TickAPI.encode(security, start), TickAPI.encode(security, stop) - 1
        db.executeone(QueryAPI("BEGIN"))
        try:
            for chunk in cls._covering_(db, first, last): db.executeone(QueryAPI(f'DELETE FROM {chunk} WHERE "UID" BETWEEN :low: AND :high:'), low=first, high=last)
            if not frame.is_empty(): db.copy(schema="Market", table="Tick", data=cls._rows_(security, frame, by))
            db.executeone(QueryAPI("COMMIT"))
        except BaseException:
            with suppress(Exception): db.executeone(QueryAPI("ROLLBACK"))
            raise
        return frame.height

    @classmethod
    def extend(cls, db: PostgresDatabaseAPI, security: int, frame: pl.DataFrame, start: datetime, by: str) -> int:
        frame = frame.filter(pl.col("Stamp") >= datetime_to_epoch(start))
        if not frame.is_empty(): db.upsert(schema="Market", table="Tick", data=cls._rows_(security, frame, by), key=["UID"])
        return frame.height

    @classmethod
    def compress(cls, db: PostgresDatabaseAPI, security: int, before: datetime) -> int:
        low, high = TickAPI.encode(security, datetime(1970, 1, 1)), TickAPI.encode(security, before)
        chunks = db.executeone(QueryAPI("""SELECT QUOTE_IDENT(chunk_schema) || '.' || QUOTE_IDENT(chunk_name) AS "Chunk" FROM timescaledb_information.chunks WHERE hypertable_schema = 'Market' AND hypertable_name = 'Tick'
            AND NOT is_compressed AND range_start_integer >= :low: AND range_end_integer <= :high: ORDER BY range_start_integer"""), low=low, high=high).fetchall(legacy=False)
        for chunk in chunks["Chunk"].to_list() if chunks.height else []: db.executeone(QueryAPI(f"SELECT compress_chunk('{chunk}', if_not_compressed => TRUE)"))
        return chunks.height

    @staticmethod
    def route(db: PostgresDatabaseAPI, security: SecurityAPI, asset: str, account: str) -> Union[tuple[int, bool, str], None]:
        if asset == account: return None
        for ticker, inverse in ((f"{asset}{account}", False), (f"{account}{asset}", True)):
            if ticker == security.Ticker.UID: return security.UID, inverse, ticker
            condition, parameters = db.where(Provider=security.Provider.UID, Ticker=ticker)
            row = db.first(schema=SecurityAPI.Schema, table=SecurityAPI.Table, condition=condition, parameters=parameters)
            if row is not None: return row[str(SecurityAPI.ID.UID)], inverse, ticker
        raise ValueError(f"Conversion {asset} to {account}: Failed · Due to no direct pair ({asset}{account} or {account}{asset})")

    @classmethod
    def compose(cls, first: tuple[TapeAPI, bool], second: tuple[TapeAPI, bool]) -> TapeAPI:
        stamps = np.union1d(first[0].Stamps, second[0].Stamps)
        (first_asks, first_bids), (second_asks, second_bids) = cls.rates(stamps, first), cls.rates(stamps, second)
        known = ~(np.isnan(first_asks) | np.isnan(second_asks))
        return TapeAPI(Security=0, Stamps=stamps[known], Asks=(first_asks * second_asks)[known], Bids=(first_bids * second_bids)[known], Volumes=np.zeros(int(known.sum())))

    @classmethod
    def legs(cls, db: PostgresDatabaseAPI, security: SecurityAPI, asset: str, account: str, bridge: Union[str, Missing] = MISSING) -> list[tuple[int, bool, str]]:
        try: route = cls.route(db, security, asset, account)
        except ValueError:
            if not bridge or bridge in (asset, account): raise
            return [leg for pair in ((asset, bridge), (bridge, account)) for leg in cls.legs(db, security, *pair)]
        return [] if route is None else [route]

    @classmethod
    def source(cls, db: PostgresDatabaseAPI, security: SecurityAPI, asset: str, account: str, tape: TapeAPI, workers: int = 32, shelf: Union[dict, Missing] = MISSING, bridge: Union[str, Missing] = MISSING) -> Union[tuple[TapeAPI, bool], None]:
        try: route = cls.route(db, security, asset, account)
        except ValueError:
            if not bridge or bridge in (asset, account): raise
            return cls.compose(cls.source(db, security, asset, bridge, tape, workers, shelf), cls.source(db, security, bridge, account, tape, workers, shelf)), False
        if route is None: return None
        uid, inverse, ticker = route
        if uid == security.UID: return tape, inverse
        source = cls.read(db, uid, epoch_to_datetime(int(tape.Stamps[0])) - timedelta(days=7), epoch_to_datetime(int(tape.Stamps[-1])), workers=workers, shelf=(shelf or {}).get(uid, MISSING))
        if not source.Stamps.size or source.Stamps[0] > tape.Stamps[0]: raise ValueError(f"Conversion {asset} to {account}: Failed · Due to no {ticker} quote before {epoch_to_datetime(int(tape.Stamps[0]))}")
        return source, inverse

    @staticmethod
    def securities(db: PostgresDatabaseAPI) -> list[int]:
        frame = db.executeone(QueryAPI(f'''SELECT DISTINCT range_start_integer >> {TickAPI.bits()} AS "Security" FROM timescaledb_information.chunks WHERE hypertable_schema = 'Market' AND hypertable_name = 'Tick' ORDER BY 1''')).fetchall(legacy=False)
        return frame["Security"].to_list() if frame.height else []

    @classmethod
    def first(cls, db: PostgresDatabaseAPI, security: int) -> Union[datetime, None]:
        low, high = cls._bounds_(security)
        uid = db.executeone(QueryAPI(f'SELECT MIN("UID") AS "UID" FROM {cls._table_()} WHERE "UID" BETWEEN :low: AND :high:'), low=low, high=high).fetchall(legacy=False).item()
        return epoch_to_datetime(uid - low) if uid is not None else None

    @classmethod
    def read(cls, db: PostgresDatabaseAPI, security: int, start: datetime, stop: datetime, workers: int = 32, shelf: Union[TapeAPI, Missing] = MISSING, shared: bool = False) -> TapeAPI:
        bounds = datetime_to_epoch(start), datetime_to_epoch(stop)
        if shelf is not MISSING and shelf.covers(*bounds): return shelf.cut(*bounds)
        low, high = TickAPI.encode(security, start), TickAPI.encode(security, stop)
        parts = [part for part in cls._parts_(db, cls._spans_(low, high), workers) if part[0].size]
        offsets = np.cumsum([0, *(rows.size for rows, _ in parts)])
        size = int(offsets[-1])
        tape = cls._allocate_(security, size, bounds, shared)
        if not size: return tape
        leads = [cls._previous_(db, security, low), *((int(rows["Ask"][-1]), int(rows["Bid"][-1])) for rows, _ in parts[:-1])]
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(parts)))) as pool: list(pool.map(lambda index: tape._decode_(parts[index], int(offsets[index]), leads[index]), range(len(parts))))
        return tape

    def slice(self, first: int, last: int) -> TapeAPI:
        return TapeAPI(Security=self.Security, Stamps=self.Stamps[first:last + 1], Asks=self.Asks[first:last + 1], Bids=self.Bids[first:last + 1], Volumes=self.Volumes[first:last + 1], Memory=self.Memory)

    def covers(self, low: int, high: int) -> bool:
        return self.Bounds is not None and self.Bounds[0] <= low and high <= self.Bounds[1]

    def cut(self, low: int, high: int) -> TapeAPI:
        first, last = int(np.searchsorted(self.Stamps, low, side="left")), int(np.searchsorted(self.Stamps, high, side="right"))
        return TapeAPI(Security=self.Security, Stamps=self.Stamps[first:last], Asks=self.Asks[first:last], Bids=self.Bids[first:last], Volumes=self.Volumes[first:last], Bounds=(low, high), Memory=self.Memory)

    def handle(self) -> tuple:
        return self.Security, self.Memory.name if self.Memory is not None else None, self.Stamps.size, self.Bounds

    @classmethod
    def attach(cls, handle: tuple) -> TapeAPI:
        security, name, size, bounds = handle
        if name is None: return cls(Security=security, Stamps=np.empty(0, dtype=np.int64), Asks=np.empty(0), Bids=np.empty(0), Volumes=np.empty(0), Bounds=bounds)
        return cls._view_(security, BlockAPI(name=name), size, bounds, False)

    def frame(self) -> pl.DataFrame:
        return pl.DataFrame({"Timestamp": self._moments_(self.Stamps), "Ask": self.Asks, "Bid": self.Bids, "Volume": self.Volumes})

    @staticmethod
    def rates(stamps: np.ndarray, source: Union[tuple[TapeAPI, bool], None]) -> tuple[np.ndarray, np.ndarray]:
        if source is None: return np.ones(stamps.size), np.ones(stamps.size)
        tape, inverse = source
        if not tape.Stamps.size: return np.full(stamps.size, np.nan), np.full(stamps.size, np.nan)
        index = np.searchsorted(tape.Stamps, stamps, side="right") - 1
        found, index = index >= 0, np.maximum(index, 0)
        asks, bids = np.where(found, tape.Asks[index], np.nan), np.where(found, tape.Bids[index], np.nan)
        return (1.0 / bids, 1.0 / asks) if inverse else (asks, bids)

    def bars(self, timeframe: TimeframeAPI, zone: str = "America/New_York", roll: int = 17, workers: int = 32) -> pl.DataFrame:
        size = self.Stamps.size
        if not size: return pl.DataFrame(schema={"Timestamp": pl.Int64, **{name: pl.Int64 for name in ("Gap", "Open", "HighAsk", "HighBid", "HighMid", "LowAsk", "LowBid", "LowMid", "Close")}, "Volume": pl.Float64})
        shift = (24 - roll) * 3_600_000
        with ThreadPoolExecutor(max_workers=workers) as pool:
            if timeframe.IsTick:
                starts = np.arange(0, size, timeframe.Value or 1, dtype=np.int64)
            else:
                edges, offsets = self._zone_(int(self.Stamps[0]), int(self.Stamps[-1]), zone)
                starts, heads = self._starts_(pool, edges, offsets + shift, timeframe)
            extremes = self._extremes_(pool, starts)
        if timeframe.IsTick:
            labels = self.Stamps[starts]
        else:
            origins = self._origins_(heads, timeframe)
            fallback = origins - shift - offsets[np.searchsorted(edges, self.Stamps[starts], side="right") - 1]
            labels = pl.Series(origins - shift).cast(pl.Datetime("ms")).dt.replace_time_zone(zone, ambiguous="earliest", non_existent="null").dt.convert_time_zone("UTC").dt.replace_time_zone(None).cast(pl.Int64).fill_null(pl.Series(fallback)).to_numpy()
        return pl.DataFrame({
            "Timestamp": labels,
            "Gap": np.maximum(starts - 1, 0),
            "Open": starts,
            "HighAsk": extremes["HighAsk"],
            "HighBid": extremes["HighBid"],
            "HighMid": extremes["HighMid"],
            "LowAsk": extremes["LowAsk"],
            "LowBid": extremes["LowBid"],
            "LowMid": extremes["LowMid"],
            "Close": np.append(starts[1:], size) - 1,
            "Volume": extremes["Volume"]
        })

    @classmethod
    def floor(cls, moment: datetime, timeframe: TimeframeAPI, zone: str = "America/New_York", roll: int = 17) -> datetime:
        one = cls(Security=0, Stamps=np.array([datetime_to_epoch(moment)], dtype=np.int64), Asks=np.zeros(1), Bids=np.zeros(1), Volumes=np.zeros(1))
        return epoch_to_datetime(int(one.bars(timeframe, zone, roll, workers=1)["Timestamp"][0]))

    @classmethod
    def reach(cls, start: datetime, stop: datetime, timeframe: TimeframeAPI, zone: str = "America/New_York", roll: int = 17) -> tuple[datetime, datetime]:
        return cls.floor(start, timeframe, zone, roll), stop + cls._length_(timeframe) + timedelta(days=2)

    @classmethod
    def span(cls, db: PostgresDatabaseAPI, security: int, timeframe: TimeframeAPI, start: datetime, stop: datetime, zone: str = "America/New_York", roll: int = 17, workers: int = 32, shelf: Union[TapeAPI, Missing] = MISSING, bars: Union[pl.DataFrame, Missing] = MISSING) -> tuple[TapeAPI, pl.DataFrame]:
        tape = cls.read(db, security, *cls.reach(start, stop, timeframe, zone, roll), workers, shelf)
        return tape, bars if bars is not MISSING else tape.bars(timeframe, zone, roll, workers).filter(pl.col("Timestamp") <= datetime_to_epoch(stop))

    @classmethod
    def before(cls, db: PostgresDatabaseAPI, security: int, timeframe: TimeframeAPI, stop: datetime, count: int, zone: str = "America/New_York", roll: int = 17, workers: int = 32, shelf: Union[TapeAPI, Missing] = MISSING) -> tuple[TapeAPI, pl.DataFrame]:
        if count <= 0:
            tape = cls.empty(security)
            return tape, tape.bars(timeframe, zone, roll)
        stop, first = cls.floor(stop, timeframe, zone, roll), MISSING
        reach = cls._length_(timeframe) * count * 1.5 + timedelta(days=4)
        while True:
            begin = cls.floor(stop - reach, timeframe, zone, roll)
            tape = cls.read(db, security, begin, stop - timedelta(milliseconds=1), workers, shelf)
            bars = tape.bars(timeframe, zone, roll, workers)
            if bars.height >= count: return tape, bars.tail(count)
            if first is MISSING: first = cls.first(db, security)
            if first is None or begin <= first: return tape, bars.tail(count)
            reach *= 2

    def materialize(self, bars: pl.DataFrame, timeframe: TimeframeAPI, base: Union[tuple, None, Missing] = MISSING, quote: Union[tuple, None, Missing] = MISSING) -> pl.DataFrame:
        ticks, columns = {}, {}
        for point, sources in (("GapPoint", ("Gap", "Gap", "Gap")), ("OpenPoint", ("Open", "Open", "Open")), ("HighPoint", ("HighAsk", "HighBid", "HighMid")), ("LowPoint", ("LowAsk", "LowBid", "LowMid")), ("ClosePoint", ("Close", "Close", "Close"))):
            for side, source in zip(("AskTick", "BidTick", "MidTick"), sources):
                if source not in ticks: ticks[source] = self._ticks_(bars[source].to_numpy(), base, quote)
                columns.update((f"{point}.{side}.{name}", values) for name, values in ticks[source].items())
        columns["Volume"] = bars["Volume"]
        columns["Security"] = np.full(bars.height, self.Security, dtype=np.int64)
        columns["Timeframe"] = pl.repeat(timeframe.UID, bars.height, dtype=pl.String, eager=True)
        columns["Timestamp"] = self._moments_(bars["Timestamp"].to_numpy())
        return pl.DataFrame(columns)

class ShareAPI:

    def __init__(self, tapes: list[TapeAPI]) -> None:
        self._tapes_ = tapes

    @staticmethod
    def attach(handles: list[tuple]) -> dict[int, TapeAPI]:
        return {handle[0]: TapeAPI.attach(handle) for handle in handles}

    def handles(self) -> list[tuple]:
        return [tape.handle() for tape in self._tapes_]

    def tapes(self) -> dict[int, TapeAPI]:
        return {tape.Security: tape for tape in self._tapes_}

    def size(self) -> int:
        return sum(32 * tape.Stamps.size for tape in self._tapes_)

    def close(self) -> None:
        blocks = [tape.Memory for tape in self._tapes_ if tape.Memory is not None]
        self._tapes_ = []
        for block in blocks:
            block.unlink()
            try: block.close()
            except BufferError: pass