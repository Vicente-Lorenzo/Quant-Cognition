from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field, InitVar
from typing import Union, ClassVar, TYPE_CHECKING, Any

from Library.Database.Dataframe import pl
from Library.Database.Dataclass import DataclassAPI
from Library.Database.Database import IdentityKey, PrimaryKey, ForeignKey
from Library.Database.Query import QueryAPI
from Library.Utility.Typing import MISSING

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI

@dataclass
class DatapointAPI(DataclassAPI):

    Database: ClassVar[str] = "Quant"
    Schema: ClassVar[str]
    Table: ClassVar[str]

    CreatedAt: Union[datetime, None] = field(default=None, kw_only=True)
    CreatedBy: Union[str, None] = field(default=None, kw_only=True)
    UpdatedAt: Union[datetime, None] = field(default=None, kw_only=True)
    UpdatedBy: Union[str, None] = field(default=None, kw_only=True)

    db: InitVar[Union[DatabaseAPI, None]] = field(default=None, kw_only=True)
    migrate: InitVar[bool] = field(default=False, kw_only=True)
    autosave: InitVar[bool] = field(default=False, kw_only=True)
    autoload: InitVar[bool] = field(default=False, kw_only=True)
    autooverload: InitVar[bool] = field(default=False, kw_only=True)

    _db_: Union[DatabaseAPI, None] = field(default=None, init=False, repr=False)
    _migrate_: bool = field(default=False, init=False, repr=False)
    _autosave_: bool = field(default=False, init=False, repr=False)
    _autoload_: bool = field(default=False, init=False, repr=False)
    _autooverload_: bool = field(default=False, init=False, repr=False)

    @property
    def Key(self) -> dict:
        return {}

    @property
    def Columns(self) -> dict:
        return {
            self.ID.CreatedAt: pl.Datetime(),
            self.ID.CreatedBy: pl.String(),
            self.ID.UpdatedAt: pl.Datetime(),
            self.ID.UpdatedBy: pl.String()
        }

    @property
    def Structure(self) -> dict:
        return {
            **self.Key,
            **self.Columns
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        self._db_, self._migrate_, self._autosave_, self._autoload_, self._autooverload_ = db, migrate, autosave, autoload, autooverload
        if self._db_ is not None:
            if self._migrate_: self._db_.migrate(schema=self.Schema, table=self.Table, structure=self.Structure)
            if self._autooverload_: self.overload()
            elif self._autoload_: self.load()

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if getattr(self, "_autosave_", False) and name and name[0].isupper():
            try: self.save(by="Autosave")
            except Exception: pass

    def primary_keys(self) -> list[str]:
        return [str(n) for n, d in self.Structure.items() if isinstance(d, PrimaryKey) or (isinstance(d, (IdentityKey, ForeignKey)) and getattr(d, "primary", False))]

    def foreign_keys(self) -> list[str]:
        return [str(n) for n, d in self.Structure.items() if isinstance(d, ForeignKey)]

    def identity_keys(self) -> list[str]:
        return [str(n) for n, d in self.Structure.items() if isinstance(d, IdentityKey) and not getattr(d, "primary", False)]

    def natural_keys(self) -> list[str]:
        return self.primary_keys()

    def identifier(self) -> dict[str, Any]:
        data_dict = self.dict(include_fields=True, include_initvar_fields=False, include_override_fields=True, include_properties=False)
        id_keys = self.identity_keys()
        if id_keys and all(data_dict.get(k) not in (None, MISSING) for k in id_keys):
            return {k: data_dict[k] for k in id_keys}
        nat_keys = self.natural_keys()
        if nat_keys and all(data_dict.get(k) not in (None, MISSING) for k in nat_keys):
            return {k: data_dict[k] for k in nat_keys}
        return {}

    def _push_(self, by: str) -> None:
        if self._db_ is None: return
        now = datetime.now()
        save_state = self._autosave_
        try:
            self._autosave_ = False
            if not self.CreatedBy: self.CreatedBy, self.CreatedAt = by, now
            self.UpdatedBy, self.UpdatedAt = by, now
            natural_key = self.natural_keys()
            identity_cols = self.identity_keys()
            data = {k: v for k, v in self.dict(include_fields=True, include_initvar_fields=False, include_properties=False, include_override_fields=True).items() if v is not None and v is not MISSING and k[0].isupper()}
            exclude = ["CreatedAt", "CreatedBy"]
            if natural_key and all(data.get(k) is not None for k in natural_key):
                insert_data = {k: v for k, v in data.items() if k not in identity_cols}
                result = self._db_.upsert(
                    schema=self.Schema, table=self.Table, data=insert_data, key=natural_key,
                    exclude=exclude,
                    returning=identity_cols if identity_cols else None
                )
                if identity_cols and hasattr(result, "is_empty") and not result.is_empty():
                    row = result.row(0, named=True)
                    for col in identity_cols:
                        if row.get(col) is not None: setattr(self, col, row[col])
            elif identity_cols and all(data.get(k) is not None for k in identity_cols):
                update_data = {k: v for k, v in data.items() if k not in identity_cols and k not in exclude}
                if update_data:
                    sql = f"UPDATE {self._db_._target_(self.Schema, self.Table)} SET "
                    sql += ", ".join([f'"{k}" = :{k}:' for k in update_data.keys()])
                    sql += " WHERE " + " AND ".join([f'"{k}" = :{k}:' for k in identity_cols])
                    params = {**update_data, **{k: data[k] for k in identity_cols}}
                    self._db_.execute(QueryAPI(sql), [params])
            else:
                fallback_key = identity_cols or natural_key or list(self.Structure.keys())[:1]
                self._db_.upsert(schema=self.Schema, table=self.Table, data=data, key=fallback_key, exclude=exclude)
        finally:
            self._autosave_ = save_state

    def save(self, by: str = "Autosave") -> None:
        self._push_(by=by)

    def _fetch_(self, condition: str, parameters: dict, overload: bool) -> Union[dict, None]:
        if self._db_ is None: return None
        df = self._db_.select(schema=self.Schema, table=self.Table, condition=condition, parameters=parameters, limit=1, legacy=False)
        if df.is_empty(): return None
        row = df.row(0, named=True)
        save_state, self._autosave_ = self._autosave_, False
        try:
            for k, v in row.items():
                if hasattr(self, k) and v is not None:
                    if overload or getattr(self, k) is None or getattr(self, k) is MISSING:
                        setattr(self, k, v)
        finally: self._autosave_ = save_state
        return row

    def _pull_(self, overload: bool) -> Union[dict, None]:
        if self._db_ is None: return None
        ident = self.identifier()
        if not ident: return None
        return self._fetch_(condition=" AND ".join([f'"{k}" = :{k}:' for k in ident.keys()]), parameters=ident, overload=overload)

    def overload(self) -> Union[dict, None]:
        return self._pull_(overload=True)

    def load(self) -> Union[dict, None]:
        return self._pull_(overload=False)