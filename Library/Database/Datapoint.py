from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING, Sequence, Any
from datetime import datetime
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Dataclass import DataclassAPI
from Library.Database.Database import IdentityKey
from Library.Utility.Typing import MISSING

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

@dataclass(kw_only=True)
class DatapointAPI(DataclassAPI):

    Database: ClassVar[str] = "Quant"
    Schema: ClassVar[str]
    Table: ClassVar[str]

    CreatedAt: datetime | None = field(default=None, init=True, repr=True)
    CreatedBy: str | None = field(default=None, init=True, repr=True)
    UpdatedAt: datetime | None = field(default=None, init=True, repr=True)
    UpdatedBy: str | None = field(default=None, init=True, repr=True)

    db: InitVar[DatabaseAPI | None] = field(default=None, init=True, repr=False)
    migrate: InitVar[bool] = field(default=False, init=True, repr=False)
    autosave: InitVar[bool] = field(default=False, init=True, repr=False)
    autoload: InitVar[bool] = field(default=False, init=True, repr=False)
    autooverload: InitVar[bool] = field(default=False, init=True, repr=False)

    _db_: DatabaseAPI | None = field(default=None, init=False, repr=False)
    _migrate_: bool = field(default=False, init=False, repr=False)
    _save_: bool = field(default=False, init=False, repr=False)
    _load_: bool = field(default=False, init=False, repr=False)
    _overload_: bool = field(default=False, init=False, repr=False)

    @classmethod
    def Structure(cls) -> dict:
        return {
            cls.ID.CreatedAt: pl.Datetime(),
            cls.ID.CreatedBy: pl.String(),
            cls.ID.UpdatedAt: pl.Datetime(),
            cls.ID.UpdatedBy: pl.String()
        }

    def __post_init__(self,
                      db: DatabaseAPI | None = None,
                      migrate: bool = False,
                      autosave: bool = False,
                      autoload: bool = False,
                      autooverload: bool = False) -> None:
        self._db_, self._migrate_, self._save_, self._load_, self._overload_ = db, migrate, autosave, autoload, autooverload
        if self._db_ is not None:
            if self._migrate_: self._db_.migrate(schema=self.Schema, table=self.Table, structure=self.Structure())
            if self._overload_: self.overload()
            elif self._load_: self.load()

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if getattr(self, "_save_", False) and name and name[0].isupper():
            try: self.save(by="Autosave")
            except Exception: pass

    def _push_(self, by: str, key: str | Sequence[str] | None) -> None:
        if self._db_ is None: return
        now = datetime.now()
        if not self.CreatedBy: self.CreatedBy, self.CreatedAt = by, now
        self.UpdatedBy, self.UpdatedAt = by, now
        if key is None:
            structure = self.Structure()
            key = [k for k, dtype in structure.items() if isinstance(dtype, IdentityKey) or getattr(dtype, 'primary', False) or type(dtype).__name__ in ('PrimaryKey', 'IdentityKey')]
            if not key: key = None
        data = {k: v for k, v in self.dict(include_fields=True, include_initvar_fields=False, include_properties=False, include_override_fields=True).items() if v is not None and k[0].isupper()}
        self._db_.upsert(schema=self.Schema, table=self.Table, data=data, key=key, exclude=["CreatedAt", "CreatedBy"])

    def save(self, by: str = "Autosave", key: str | Sequence[str] | None = None) -> None:
        self._push_(by=by, key=key)

    def _pull_(self, condition: str | None, parameters: dict | None, overload: bool) -> dict | None:
        if self._db_ is None: return None
        if condition is None:
            structure = self.Structure()
            pk_cols = [k for k, dtype in structure.items() if isinstance(dtype, IdentityKey) or getattr(dtype, 'primary', False) or type(dtype).__name__ in ('PrimaryKey', 'IdentityKey')]
            if not pk_cols: return None
            data_dict = self.dict(include_fields=True, include_initvar_fields=False, include_override_fields=True, include_properties=False)
            conds, params = [], {}
            for pk in pk_cols:
                val = data_dict.get(pk)
                if val is None or val is MISSING: return None
                conds.append(f'"{pk}" = :{pk}:')
                params[pk] = val
            condition, parameters = " AND ".join(conds), params
        if not condition: return None
        df = self._db_.select(schema=self.Schema, table=self.Table, condition=condition, parameters=parameters, limit=1, legacy=False)
        if df.is_empty(): return None
        row = df.row(0, named=True)
        save_state = self._save_
        self._save_ = False
        try:
            for k, v in row.items():
                if hasattr(self, k) and v is not None:
                    if overload or getattr(self, k) is None or getattr(self, k) is MISSING: setattr(self, k, v)
        finally: self._save_ = save_state
        return row

    def overload(self, condition: str | None = None, parameters: dict | None = None) -> dict | None:
        return self._pull_(condition=condition, parameters=parameters, overload=True)

    def load(self, condition: str | None = None, parameters: dict | None = None) -> dict | None:
        return self._pull_(condition=condition, parameters=parameters, overload=False)