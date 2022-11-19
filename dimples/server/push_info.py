# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2022 Albert Moky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

"""
    Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional

from dimsdk import json_encode, json_decode


class PushAlert:
    """
        Alert
        ~~~~~

        "alert": {
            "title"    : "{TITLE}",
            "subtitle" : "{SUBTITLE}",
            "body"     : "{CONTENT}",
            "image"    : "{URL}"
        }
    """

    def __init__(self, title: Optional[str], subtitle: Optional[str], body: str, image: Optional[str]):
        super().__init__()
        self.__title = title
        self.__subtitle = subtitle
        self.__body = body
        self.__image = image  # URL

    @property
    def title(self) -> Optional[str]:
        return self.__title

    @property
    def subtitle(self) -> Optional[str]:
        return self.__subtitle

    @property
    def body(self) -> str:
        return self.__body

    @property
    def image(self) -> Optional[str]:
        return self.__image

    def __str__(self) -> str:
        return self.to_json()

    def __repr__(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        info = {
            'body': self.__body
        }
        if self.__title is not None:
            info['title'] = self.__title
        if self.__subtitle is not None:
            info['subtitle'] = self.__subtitle
        if self.__image is not None:
            info['image'] = self.__image
        # encode
        return json_encode(obj=info)

    @classmethod
    def from_json(cls, string: str):
        info = json_decode(string=string)
        return cls.from_dict(dictionary=info)

    @classmethod
    def from_dict(cls, dictionary: dict):
        title = dictionary.get('title')
        subtitle = dictionary.get('subtitle')
        body = dictionary.get('body')
        image = dictionary.get('image')
        assert body is not None, 'alert.body should not be empty'
        return cls(title=title, subtitle=subtitle, body=body, image=image)


class PushInfo:
    """
        Push Info
        ~~~~~~~~~

        "aps": {
            "alert"    : {
                // ...
            },
            "title"    : "{TITLE}",   // alert.title
            "content"  : "{CONTENT},  // alert.body
            "sound"    : "{URL}",
            "badge"    : 0,
            "category" : "{CATEGORY}"
        }
    """

    def __init__(self, alert: PushAlert,
                 title: str = None, content: str = None, sound: str = None, badge: int = 0, category: str = None):
        super().__init__()
        self.__alert = alert
        self.__title = title
        self.__content = content
        self.__sound = sound  # URL
        self.__badge = badge
        self.__category = category

    @property
    def alert(self) -> PushAlert:
        return self.__alert

    @property
    def title(self) -> Optional[str]:
        text = self.__title
        if text is None:
            text = self.__alert.title
        return text

    @property
    def content(self) -> str:
        text = self.__content
        if text is None:
            text = self.__alert.body
        return text

    @property
    def image(self) -> Optional[str]:
        return self.__alert.image

    @property
    def sound(self) -> Optional[str]:
        return self.__sound

    @property
    def badge(self) -> int:
        cnt = self.__badge
        return 0 if cnt is None else cnt

    @property
    def category(self) -> Optional[str]:
        return self.__category

    def __str__(self) -> str:
        return self.to_json()

    def __repr__(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        info = {
            'alert': self.__alert
        }
        if self.__title is not None:
            info['title'] = self.__title
        if self.__content is not None:
            info['content'] = self.__content
        if self.__sound is not None:
            info['sound'] = self.__sound
        if self.__badge > 0:
            info['badge'] = self.__badge
        if self.__category is not None:
            info['category'] = self.__category
        # encode
        return json_encode(obj=info)

    @classmethod
    def from_json(cls, string: str):
        info = json_decode(string=string)
        return cls.from_dict(dictionary=info)

    @classmethod
    def from_dict(cls, dictionary: dict):
        alert = dictionary.get('alert')
        title = dictionary.get('title')
        content = dictionary.get('content')
        sound = dictionary.get('sound')
        badge = dictionary.get('badge')
        category = dictionary.get('category')
        assert alert is not None, 'alert should not be empty'
        if badge is None:
            badge = 0
        return cls(alert=PushAlert.from_dict(dictionary=alert),
                   title=title, content=content, sound=sound, badge=badge, category=category)

    @classmethod
    def create(cls, content: str, title: str = None, image: str = None, badge: int = 0, sound: str = None):
        alert = PushAlert(title=title, subtitle=None, body=content, image=image)
        return PushInfo(alert=alert, badge=badge, sound=sound)
