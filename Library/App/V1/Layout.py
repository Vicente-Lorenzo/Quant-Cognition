from dash import html
from abc import ABC, abstractmethod

from Library.App.V1.Component import Component, parse_classname

class LayoutAPI(Component, ABC):

    @abstractmethod
    def build(self) -> Component:
        raise NotImplementedError

    def __repr__(self) -> str:
        return repr(self.build())

class DefaultLayoutAPI(LayoutAPI):

    def __init__(self, *,
                 image: str = None,
                 title: str = None,
                 description: str = None,
                 details: str = None,
                 classname: str = None) -> None:
        super().__init__()
        self._image_: str = image
        self._title_: str = title
        self._description_: str = description
        self._details_: str = details
        self._classname_: str = classname

    def build(self) -> Component:
        return html.Div([
            html.Img(src=self._image_, alt=self._title_, className="image"),
            html.H2(self._title_, className="title"),
            html.P(self._description_, className="description"),
            html.P(self._details_, className="details"),
        ], className=parse_classname(basename="layout", classname=self._classname_))