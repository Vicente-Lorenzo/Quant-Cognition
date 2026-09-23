import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Union

from Library.Auth.Access import AccessLevel, AccessAPI
from Library.Auth.Role import RoleAPI
from Library.Auth.User import UserAPI
from Library.Credential.Credential import Validity, CredentialAPI
from Library.Credential.Type import LayoutAPI
from Library.Credential.Secret import SecretAPI
from Library.Database import PostgresDatabaseAPI
from Library.Logging import LoggingAPI
from Library.Utility.Datetime import INSTANT, utc_now
from Library.Utility.Typing import MISSING, Missing

class VaultAPI:

    def __init__(self, *, database: str = "Quant", margin: int = 7 * 86400, refreshers: Union[dict[str, Callable], Missing] = MISSING) -> None:
        self._database_ = database
        self._margin_ = margin
        self._refreshers_ = dict(refreshers) if refreshers else {}
        self._log_ = LoggingAPI(database)

    @property
    def Margin(self) -> int:
        return self._margin_

    def scope(self):
        return PostgresDatabaseAPI.scope(database=self._database_)

    def validity(self, expires: Union[datetime, None], now: Union[datetime, None] = None) -> Validity:
        if expires is None: return Validity.Permanent
        now = now or utc_now()
        if expires <= now: return Validity.Expired
        return Validity.Expiring if expires <= now + timedelta(seconds=self._margin_) else Validity.Valid

    @staticmethod
    def _clean_(fields: dict) -> dict:
        return {key: value for key, value in fields.items() if value is not None or key in CredentialAPI.Nullable}

    def _user_(self, by) -> Union[UserAPI, None]:
        if isinstance(by, UserAPI): return by
        if not by: return None
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            condition, parameters = db.where(UID=str(by))
            row = db.first(schema=UserAPI.Schema, table=UserAPI.Table, condition=condition, parameters=parameters)
        return None if row is None else UserAPI.parse(row)

    def principal(self, by) -> tuple:
        user = self._user_(by)
        return (user.UID if user is not None else None), RoleAPI.coerce(user.Role if user is not None else None)

    def administrator(self) -> Union[str, None]:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            condition, parameters = db.where(Role=RoleAPI.Administrator.name)
            row = db.first(schema=UserAPI.Schema, table=UserAPI.Table, condition=condition, order='"UID" ASC', parameters=parameters)
        return None if row is None else row.get("UID")

    def _stamp_(self, by, uid: Union[str, None]) -> str:
        return uid or (by if isinstance(by, str) and by else "Anonymous")

    def _select_(self, **columns) -> list[dict]:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            condition, parameters = db.where(**columns)
            return db.records(schema=CredentialAPI.Schema, table=CredentialAPI.Table, condition=condition, order='"Service" ASC, "Name" ASC', parameters=parameters)

    def _one_(self, uid: str) -> Union[dict, None]:
        if not uid: return None
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            condition, parameters = db.where(UID=uid)
            return db.first(schema=CredentialAPI.Schema, table=CredentialAPI.Table, condition=condition, parameters=parameters)

    def _save_(self, credential: CredentialAPI, by: str) -> None:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            credential._db_ = db
            credential.save(by=by)
        credential._db_ = None

    def _erase_(self, uid: str, row: dict, fields: dict) -> None:
        cleared = [name for name, value in fields.items() if value is None and row.get(name) is not None]
        if not cleared: return
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            condition, parameters = db.where(UID=uid)
            db.update(schema=CredentialAPI.Schema, table=CredentialAPI.Table, data={name: None for name in cleared}, condition=condition, parameters=parameters)

    def _thresholds_(self, view, edit, role: RoleAPI, previous: tuple = (None, None)) -> tuple:
        view, edit = AccessAPI.validate(view, edit, names=("ViewRole", "EditRole"), setter=role, previous=previous)
        return (view.name if view is not None else None), (edit.name if edit is not None else None)

    @staticmethod
    def _expiry_(value) -> Union[datetime, None]:
        if value is None or value == "": return None
        if isinstance(value, datetime): return value
        text = str(value).strip()
        try: return datetime.strptime(text, INSTANT)
        except ValueError: pass
        try: parsed = datetime.fromisoformat(text)
        except ValueError: raise ValueError(f"Credential Expiry: Failed · {text} is not a date · Expected YYYY-MM-DD HH:MM:SS") from None
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo is not None else parsed

    def _allows_(self, row: Union[dict, None], principal: tuple, *, edit: bool = False) -> bool:
        if row is None: return False
        user, role = principal
        return AccessAPI.allows(row.get("EditRole") if edit else row.get("ViewRole"), role=role, user=user, owner=row.get("Owner"))

    def permits(self, row: Union[dict, None], by, *, edit: bool = False) -> bool:
        return self._allows_(row, self.principal(by), edit=edit)

    def _checked_(self, credential: CredentialAPI, principal: tuple, previous: Union[dict, None] = None) -> None:
        if not credential.Service or not credential.Name: raise ValueError("Credential Store: Failed · Service and Name are required")
        if any(row["UID"] != credential.UID for row in self._select_(Service=credential.Service, Name=credential.Name)): raise ValueError(f"Credential Store: Failed · {credential.Service} · {credential.Name} already exists")
        if not credential.Parent or (previous is not None and previous.get("Parent") == credential.Parent): return
        if credential.Parent == credential.UID: raise ValueError("Credential Parent: Failed · A credential cannot be its own parent")
        parent = self._one_(credential.Parent)
        if parent is None: raise ValueError(f"Credential Parent: Failed · {credential.Parent} does not exist")
        if parent.get("Parent"): raise ValueError("Credential Parent: Failed · A parent cannot itself inherit from another credential")
        if self._select_(Parent=credential.UID): raise ValueError("Credential Parent: Failed · A credential others inherit from cannot inherit itself")
        if not self._allows_(parent, principal): raise PermissionError("Credential Parent: Failed · You may not view the parent credential")

    @staticmethod
    def _merged_(row: dict, secret: str) -> Union[str, None]:
        stored, incoming = CredentialAPI.unpack(row.get("Secret")), CredentialAPI.unpack(secret)
        if not isinstance(stored, dict) or not isinstance(incoming, dict): return secret
        merged = {name: value for name, value in {**stored, **incoming}.items() if value is not None}
        return CredentialAPI.pack(merged) if merged else None

    @staticmethod
    def _masked_(row: dict) -> dict:
        secrets = CredentialAPI.spread(row.get("Secret"), LayoutAPI.secret(row.get("Kind")))
        return {**row, "Secret": CredentialAPI.pack(SecretAPI.mask(secrets)) if secrets else None}

    def _presented_(self, row: dict, principal: tuple) -> dict:
        return {**self._masked_(row), "Access": (AccessLevel.Edit if self._allows_(row, principal, edit=True) else AccessLevel.View).name}

    def credentials(self, *, by=None, service: Union[str, Missing] = MISSING) -> list[dict]:
        principal = self.principal(by)
        return [self._presented_(row, principal) for row in self._select_(Service=service) if self._allows_(row, principal)]

    def credential(self, uid: str, *, by=None) -> Union[dict, None]:
        row, principal = self._one_(uid), self.principal(by)
        return self._presented_(row, principal) if self._allows_(row, principal) else None

    def store(self, *, by=None, **fields) -> CredentialAPI:
        principal = self.principal(by)
        user, role = principal
        if user is None: raise PermissionError("Credential Store: Failed · Only a signed-in user may store a credential")
        fields = {**CredentialAPI.Defaults, "Owner": user, **self._clean_(fields)}
        AccessAPI.claim(fields["Owner"], role=role, user=user)
        if fields["Owner"] != user and self._user_(fields["Owner"]) is None: raise ValueError(f"Credential Store: Failed · {fields['Owner']} is not a user")
        fields["ViewRole"], fields["EditRole"] = self._thresholds_(fields.get("ViewRole"), fields.get("EditRole"), role)
        fields["ExpiresAt"] = self._expiry_(fields.get("ExpiresAt"))
        credential = CredentialAPI(UID=fields.pop("UID", None) or uuid.uuid4().hex, **fields)
        if self._one_(credential.UID) is not None: raise ValueError(f"Credential Store: Failed · {credential.UID} already exists")
        self._checked_(credential, principal)
        self._save_(credential, by=user)
        self._log_.info(lambda: f"Credential Store: Saved ({credential.UID}) · {credential.Service} · {credential.Name}")
        return credential

    def update(self, uid: str, *, by=None, **fields) -> Union[CredentialAPI, None]:
        row, principal = self._one_(uid), self.principal(by)
        if not self._allows_(row, principal, edit=True): return None
        user, role = principal
        fields = self._clean_(fields)
        if fields.get("Owner", row.get("Owner")) != row.get("Owner"):
            if role is not RoleAPI.Administrator and user != row.get("Owner"): raise PermissionError("Credential Transfer: Failed · Only the owner or an Administrator may transfer a credential")
            if self._user_(fields["Owner"]) is None: raise ValueError(f"Credential Transfer: Failed · {fields['Owner']} is not a user")
        if "ViewRole" in fields or "EditRole" in fields:
            fields["ViewRole"], fields["EditRole"] = self._thresholds_(fields.get("ViewRole", row.get("ViewRole")), fields.get("EditRole", row.get("EditRole")), role, (row.get("ViewRole"), row.get("EditRole")))
        if "ExpiresAt" in fields: fields["ExpiresAt"] = self._expiry_(fields["ExpiresAt"])
        if "Secret" in fields: fields["Secret"] = self._merged_(row, fields["Secret"])
        credential = CredentialAPI.parse({**row, **fields})
        self._checked_(credential, principal, row)
        self._save_(credential, by=self._stamp_(by, user))
        self._erase_(uid, row, fields)
        self._log_.info(lambda: f"Credential Update: Saved ({uid}) · {credential.Service} · {credential.Name}")
        return credential

    def delete(self, uid: str, *, by=None) -> bool:
        row = self._one_(uid)
        if not self.permits(row, by, edit=True): return False
        children = self._select_(Parent=uid)
        if children: raise ValueError(f"Credential Delete: Failed · {len(children)} credential(s) inherit from it · {' · '.join(child['Name'] for child in children)}")
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            condition, parameters = db.where(UID=uid)
            db.remove(schema=CredentialAPI.Schema, table=CredentialAPI.Table, condition=condition, parameters=parameters)
        self._log_.info(lambda: f"Credential Delete: Removed ({uid})")
        return True

    def transfer(self, uid: str, owner: str, *, by=None) -> bool:
        return self.update(uid, by=by, Owner=owner) is not None

    def reveal(self, uid: str, *, by=None) -> Union[dict, None]:
        row, principal = self._one_(uid), self.principal(by)
        if not self._allows_(row, principal, edit=True): return None
        self._log_.debug(lambda: f"Credential Reveal: Read ({uid}) · By {self._stamp_(by, principal[0])}")
        return CredentialAPI.spread(row.get("Secret"), LayoutAPI.secret(row.get("Kind")))

    def _located_(self, uid: Union[str, Missing], service: Union[str, Missing], name: Union[str, Missing]) -> Union[dict, None]:
        if uid: return self._one_(uid)
        if not service or not name: raise ValueError("Credential Resolve: Failed · Name the credential by UID or by Service and Name")
        rows = self._select_(Service=service, Name=name)
        return rows[0] if rows else None

    def _used_(self, uid: str, by, user: Union[str, None]) -> None:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            condition, parameters = db.where(UID=uid)
            db.update(schema=CredentialAPI.Schema, table=CredentialAPI.Table, data={"UsedAt": utc_now(), "UsedBy": self._stamp_(by, user)}, condition=condition, parameters=parameters)

    def resolve(self, *, uid: Union[str, Missing] = MISSING, service: Union[str, Missing] = MISSING, name: Union[str, Missing] = MISSING, by=None) -> Union[dict, None]:
        row, principal = self._located_(uid, service, name), self.principal(by)
        if not self._allows_(row, principal): return None
        credential = CredentialAPI.parse(row)
        parent = self._one_(credential.Parent) if credential.Parent else None
        if parent is not None and not self._allows_(parent, principal): return None
        self._used_(credential.UID, by, principal[0])
        return credential.values(CredentialAPI.parse(parent) if parent is not None else None)

    def due(self, *, margin: Union[int, Missing] = MISSING) -> list[dict]:
        horizon = utc_now() + timedelta(seconds=self._margin_ if margin is MISSING else margin)
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            return db.records(schema=CredentialAPI.Schema, table=CredentialAPI.Table, condition='"ExpiresAt" IS NOT NULL AND "ExpiresAt" <= :horizon:', order='"ExpiresAt" ASC', parameters={"horizon": horizon})

    def refresh(self, uid: str, secrets: dict, *, expires=MISSING, by=None) -> Union[CredentialAPI, None]:
        row = self._one_(uid)
        if row is None: return None
        stored = CredentialAPI.spread(row.get("Secret"), LayoutAPI.secret(row.get("Kind")))
        fields = {"Secret": CredentialAPI.pack({**stored, **SecretAPI.unwrap(secrets)})}
        if expires is not MISSING: fields["ExpiresAt"] = self._expiry_(expires)
        credential = CredentialAPI.parse({**row, **fields})
        self._save_(credential, by=self._stamp_(by, self.principal(by)[0]))
        self._erase_(uid, row, fields)
        self._log_.info(lambda: f"Credential Refresh: Rotated ({uid}) · {credential.Service} · {credential.Name}")
        return credential

    def rotate(self, uid: str) -> bool:
        row = self._one_(uid)
        if row is None: return False
        refresher = self._refreshers_.get(row.get("Service"))
        if refresher is None: return False
        secrets, expires = refresher(CredentialAPI.parse(row).values())
        return self.refresh(uid, secrets, expires=expires, by="Framework") is not None

    def internal(self, *, service: str, name: str) -> Union[dict, None]:
        rows = self._select_(Service=service, Name=name)
        if not rows: return None
        self._used_(rows[0]["UID"], "Framework", None)
        return CredentialAPI.parse(rows[0]).values()

    def ensure(self, *, service: str, name: str, secret, by=None, **fields) -> CredentialAPI:
        rows = self._select_(Service=service, Name=name)
        if rows: return CredentialAPI.parse(rows[0])
        return self.store(by=by, Service=service, Name=name, Secret=CredentialAPI.pack(secret), **fields)