from dash import html
from abc import ABC, abstractmethod

from Library.App.V2.Component.Component import Component, ContainerAPI, IconAPI, TextAPI

class LayoutAPI(ABC):

    @abstractmethod
    def build(self) -> list[Component]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return repr(self.build())

class DefaultLayoutAPI(LayoutAPI):

    def __init__(self, *,
                 icon: str = None,
                 title: str = None,
                 description: str = None,
                 details: str = None,
                 classname: str = None) -> None:
        self._icon_ = icon
        self._title_ = title
        self._description_ = description
        self._details_ = details
        self._classname_ = classname

    def build(self) -> list[Component]:
        elements = []
        if self._icon_: elements.append(IconAPI(icon=self._icon_, classname="status-icon"))
        if self._title_: elements.append(TextAPI(text=self._title_, classname="status-title", builder=html.H2))
        if self._description_: elements.append(TextAPI(text=self._description_, classname="status-description", builder=html.P))
        if self._details_: elements.append(TextAPI(text=self._details_, classname="status-details", builder=html.P))
        return ContainerAPI(fluid=True, classname="status", stylename=self._classname_, elements=elements).build()