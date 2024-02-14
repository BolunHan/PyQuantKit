from __future__ import annotations

import abc
import datetime
import enum
import json
import math
import re
import warnings
from typing import overload

import numpy as np

from . import LOGGER

LOGGER = LOGGER.getChild('MarketUtils')
__all__ = ['BarData', 'MarketData', 'OrderBook', 'TickData', 'TransactionData', 'TradeData', 'TransactionSide', 'TIME_ZONE']

TIME_ZONE = None


class TransactionSide(enum.Enum):
    ShortOrder = AskOrder = Offer_to_Short = -3
    ShortOpen = Sell_to_Short = -2
    ShortFilled = LongClose = Sell_to_Unwind = ask = -1
    UNKNOWN = CANCEL = 0
    LongFilled = LongOpen = Buy_to_Long = bid = 1
    ShortClose = Buy_to_Cover = 2
    LongOrder = BidOrder = Bid_to_Long = 3

    def __lt__(self, other):
        warnings.warn(DeprecationWarning('Comparison of the <TransactionSide> deprecated!'))
        if self.__class__ is other.__class__:
            return self.value < other.value
        else:
            return self.value < other

    def __gt__(self, other):
        warnings.warn(DeprecationWarning('Comparison of the <TransactionSide> deprecated!'))
        if self.__class__ is other.__class__:
            return self.value > other.value
        else:
            return self.value > other

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.value == other.value
        else:
            return self.value == other

    def __neg__(self) -> TransactionSide:
        """
        return a opposite trade side, Long -> Short and Short -> Long
        :return: tr
        """
        if self is self.LongOpen:
            return self.LongClose
        elif self is self.LongClose:
            return self.LongOpen
        elif self is self.ShortOpen:
            return self.ShortClose
        elif self is self.ShortClose:
            return self.ShortOpen
        elif self is self.BidOrder:
            return self.AskOrder
        elif self is self.AskOrder:
            return self.BidOrder
        else:
            LOGGER.warning('No valid registered opposite trade side for {}'.format(self))
            return self.UNKNOWN

    def __hash__(self):
        return self.value

    @classmethod
    def from_offset(cls, direction: str, offset: str) -> TransactionSide:

        direction = direction.lower()
        offset = offset.lower()

        if direction in ['buy', 'long', 'b']:
            if offset in ['open', 'wind']:
                return cls.LongOpen
            elif offset in ['close', 'cover', 'unwind']:
                return cls.ShortOpen
            else:
                raise ValueError(f'Not recognized {direction} {offset}')
        elif direction in ['sell', 'short', 's']:
            if offset in ['open', 'wind']:
                return cls.ShortOpen
            elif offset in ['close', 'cover', 'unwind']:
                return cls.LongClose
            else:
                raise ValueError(f'Not recognized {direction} {offset}')
        else:
            raise ValueError(f'Not recognized {direction} {offset}')

    @classmethod
    def _missing_(cls, value: str | int):
        capital_str = str(value).capitalize()

        if capital_str == 'Long' or capital_str == 'Buy' or capital_str == 'B':
            trade_side = cls.LongOpen
        elif capital_str == 'Short' or capital_str == 'Ss':
            trade_side = cls.ShortOpen
        elif capital_str == 'Close' or capital_str == 'Sell' or capital_str == 'S':
            trade_side = cls.LongClose
        elif capital_str == 'Cover' or capital_str == 'Bc':
            trade_side = cls.ShortClose
        elif capital_str == 'Ask':
            trade_side = cls.AskOrder
        elif capital_str == 'Bid':
            trade_side = cls.BidOrder
        else:
            # noinspection PyBroadException
            try:
                trade_side = cls.__getitem__(value)
            except Exception as _:
                trade_side = cls.UNKNOWN
                LOGGER.warning('{} is not recognized, return TransactionSide.UNKNOWN'.format(value))

        return trade_side

    @property
    def sign(self) -> int:
        if self.value == self.Buy_to_Long.value or self.value == self.Buy_to_Cover.value:
            return 1
        elif self.value == self.Sell_to_Unwind.value or self.value == self.Sell_to_Short.value:
            return -1
        elif self.value == 0:
            return 0
        else:
            LOGGER.warning(f'Requesting .sign of {self.name} is not recommended, use .order_sign instead')
            return self.order_sign

    @property
    def order_sign(self) -> int:
        if self.value == self.LongOrder.value:
            return 1
        elif self.value == self.ShortOrder.value:
            return -1
        elif self.value == 0:
            return 0
        else:
            LOGGER.warning(f'Requesting .order_sign of {self.name} is not recommended, use .sign instead')
            return self.sign

    @property
    def offset(self) -> int:
        return self.sign

    @property
    def side_name(self):
        if self.value == self.Buy_to_Long.value or self.value == self.Buy_to_Cover.value:
            return 'Long'
        elif self.value == self.Sell_to_Unwind.value or self.value == self.Sell_to_Short.value:
            return 'Short'
        elif self.value == self.Offer_to_Short.value:
            return 'ask'
        elif self.value == self.Bid_to_Long.value:
            return 'bid'
        else:
            return 'Unknown'

    @property
    def offset_name(self):
        if self.value == self.Buy_to_Long.value or self.value == self.Sell_to_Short.value:
            return 'Open'
        elif self.value == self.Buy_to_Cover.value or self.value == self.Sell_to_Unwind.value:
            return 'Close'
        elif self.value == self.Offer_to_Short.value or self.value == self.Bid_to_Long.value:
            LOGGER.warning(f'Requesting offset of {self.name} is not supported, returns {self.side_name}')
            return self.side_name
        else:
            return 'Unknown'


class MarketData(dict, metaclass=abc.ABCMeta):
    def __init__(self, ticker: str, timestamp: float, **kwargs):
        super().__init__(ticker=ticker, timestamp=timestamp)

        if kwargs:
            self['additional'] = dict(kwargs)

    def __copy__(self):
        return self.__class__.__init__(**self)

    def copy(self):
        return self.__copy__()

    def to_json(self, fmt='str', **kwargs) -> str | dict:
        data_dict = dict(
            dtype=self.__class__.__name__,
            **self
        )

        if 'additional' in data_dict:
            additional = data_dict.pop('additional')
            data_dict.update(additional)

        if fmt == 'dict':
            return data_dict
        elif fmt == 'str':
            return json.dumps(data_dict, **kwargs)
        else:
            raise ValueError(f'Invalid format {fmt}, except "dict" or "str".')

    @classmethod
    def from_json(cls, json_message: str | bytes | bytearray | dict) -> MarketData:
        if isinstance(json_message, dict):
            json_dict = json_message
        else:
            json_dict = json.loads(json_message)

        dtype = json_dict.pop('dtype', None)
        if dtype == 'BarData':
            return BarData.from_json(json_dict)
        elif dtype == 'TickData':
            return TickData.from_json(json_dict)
        elif dtype == 'TransactionData':
            return TransactionData.from_json(json_dict)
        elif dtype == 'TradeData':
            return TradeData.from_json(json_dict)
        elif dtype == 'OrderBook':
            return OrderBook.from_json(json_dict)
        else:
            raise TypeError(f'Invalid dtype {dtype}')

    @abc.abstractmethod
    def to_list(self) -> list[float | int | str | bool]:
        ...

    @classmethod
    def from_list(cls, data_list: list[float | int | str | bool]) -> MarketData:
        dtype = data_list[0]

        if dtype == 'BarData':
            return BarData.from_list(data_list)
        elif dtype == 'TickData':
            return TickData.from_list(data_list)
        elif dtype == 'TransactionData':
            return TransactionData.from_list(data_list)
        elif dtype == 'TradeData':
            return TradeData.from_list(data_list)
        elif dtype == 'OrderBook':
            return OrderBook.from_list(data_list)
        else:
            raise TypeError(f'Invalid dtype {dtype}')

    @property
    def ticker(self):
        return self['ticker']

    @property
    def timestamp(self):
        return self['timestamp']

    @property
    def additional(self):
        if 'additional' not in self:
            self['additional'] = {}
        return self['additional']

    @property
    def topic(self) -> str:
        return f'{self.ticker}.{self.__class__.__name__}'

    @property
    def market_time(self) -> datetime.datetime | datetime.date:
        return datetime.datetime.fromtimestamp(self.timestamp, tz=TIME_ZONE)

    @property
    @abc.abstractmethod
    def market_price(self) -> float:
        ...


class OrderBook(MarketData):
    class Book(object):
        def __init__(self, side: int):
            self.side: int = side
            # store the entry in order of (price, volume, order, etc...)
            self._book: list[tuple[float, float, ...]] = []
            self._dict: dict[float, tuple[float, float, ...]] = {}
            self.sorted = False

        def __iter__(self):
            self.sort()
            return sorted(self._book).__iter__()

        def __getitem__(self, item):
            if isinstance(item, int) and item not in self._dict:
                return self.at_level(item)
            elif isinstance(item, float):
                return self.at_price(item)
            else:
                raise KeyError(f'Ambiguous index value {item}, please use at_price or at_level specifically')

        def __contains__(self, price: float):
            return self._dict.__contains__(price)

        def __len__(self):
            return self._book.__len__()

        def __repr__(self):
            return f'<OrderBook.Book.{"Bid" if self.side > 0 else "Ask"}>'

        def __bool__(self):
            return bool(self._book)

        def __sub__(self, other: OrderBook.Book) -> dict[float, float]:
            if not isinstance(other, self.__class__):
                raise TypeError(f'Expect type {self.__class__.__name__}, got {type(other)}')

            if self.side != other.side:
                raise ValueError(f'Expect side {self.side}, got {other.side}')

            diff = {}

            # bid book
            if (not self._dict) or (not other._dict):
                pass
            elif self.side > 0:
                limit_0 = min(self._dict)
                limit_1 = min(other._dict)
                limit = max(limit_0, limit_1)
                contain_limit = True if limit_0 == limit_1 else False

                for entry in self._book:
                    price, volume, *_ = entry

                    if price > limit or (price >= limit and contain_limit):
                        diff[price] = volume

                for entry in other._book:
                    price, volume, *_ = entry

                    if price > limit or (price >= limit and contain_limit):
                        diff[price] = diff.get(price, 0.) - volume
            # ask book
            else:
                limit_0 = max(self._dict)
                limit_1 = max(other._dict)
                limit = min(limit_0, limit_1)
                contain_limit = True if limit_0 == limit_1 else False

                for entry in self._book:
                    price, volume, *_ = entry

                    if price < limit or (price <= limit and contain_limit):
                        diff[price] = volume

                for entry in other._book:
                    price, volume, *_ = entry

                    if price < limit or (price <= limit and contain_limit):
                        diff[price] = diff.get(price, 0.) - volume

            return diff

        def get(self, item=None, **kwargs) -> tuple[float, float, ...] | None:
            if item is None:
                price = kwargs.pop('price', None)
                level = kwargs.pop('level', None)
            else:
                if isinstance(item, int):
                    price = None
                    level = item
                elif isinstance(item, float):
                    price = item
                    level = None
                else:
                    raise ValueError(f'Invalid type {type(item)}, must be int or float')

            if price is None and level is None:
                raise ValueError('Must assign either price or level in kwargs')
            elif price is None:
                try:
                    return self.at_level(level=level)
                except IndexError:
                    return None
            elif level is None:
                try:
                    return self.at_price(price=price)
                except KeyError:
                    return None
            else:
                raise ValueError('Must NOT assign both price or level in kwargs')

        def pop(self, price: float):
            entry = self._dict.pop(price, None)
            if entry is not None:
                self._book.remove(entry)
            else:
                raise KeyError(f'Price {price} not exist in order book')
            return entry

        def remove(self, entry: OrderBook.OrderBookEntry):
            try:
                self._book.remove(entry)
                self._dict.pop(entry.price)
            except ValueError:
                raise ValueError(f'Entry {entry} not exist in order book')

        def at_price(self, price: float):
            """
            get OrderBook.Book.Entry with specific price
            :param price: the given price
            :return: the logged OrderBook.Book.Entry
            """
            if price in self._dict:
                return self._dict.__getitem__(price)
            else:
                return None

        def at_level(self, level: int):
            """
            get OrderBook.Book.Entry with level num
            :param level: the given level
            :return: the logged OrderBook.Book.Entry
            """
            return self._book.__getitem__(level)

        def update(self, price: float, volume: float, order: int = None):
            if price in self._dict:
                if volume == 0:
                    self.pop(price=price)
                elif volume < 0:
                    LOGGER.warning(f'Invalid volume {volume}, expect a positive float.')
                    self.pop(price=price)
                else:
                    entry = self._dict[price]
                    entry.volume = volume
            else:
                self.add(price=price, volume=volume, order=order)

        def add(self, price: float, volume: float, order: int = None):
            entry = (price, volume, order if order else 0)
            self._dict[price] = entry
            self._book.append(entry)

        def loc_volume(self, p0: float, p1: float):
            volume = 0.
            p_min = min(p0, p1)
            p_max = max(p0, p1)

            for entry in self._book:
                price, volume, *_ = entry
                if p_min < price < p_max:
                    volume += volume

            return volume

        def sort(self):
            if self.side > 0:  # bid
                self._book.sort(reverse=True, key=lambda x: x[0])
            else:
                self._book.sort(key=lambda x: x[0])
            self.sorted = True

        @property
        def price(self):
            if not self.sorted:
                self.sort()

            return [entry[0] for entry in self._book]

        @property
        def volume(self):
            if not self.sorted:
                self.sort()

            return [entry[1] for entry in self._book]

    def __init__(self, *, ticker: str, timestamp: float, bid: list[tuple[float, float, int]] = None, ask: list[tuple[float, float, int]], **kwargs):
        super().__init__(ticker=ticker, timestamp=timestamp)
        self.update(
            bid=[] if bid is None else bid,
            ask=[] if ask is None else ask
        )
        self.parse(**kwargs)

    def __getattr__(self, item: str):
        if re.match('^((bid_)|(ask_))((price_)|(volume_))[0-9]+$', item):
            side = item.split('_')[0]
            key = item.split('_')[1]
            level = int(item.split('_')[2])
            book: 'OrderBook.Book' = self.__getattribute__(f'{side}')
            if 0 < level <= len(book):
                return book[level].__getattribute__(key)
            else:
                raise AttributeError(f'query level [{level}] exceed max level [{len(book)}]')
        else:
            raise AttributeError(f'{item} not found in {self.__class__}')

    def __setattr__(self, key, value):
        if re.match('^((bid_)|(ask_))((price_)|(volume_))[0-9]+$', key):
            self.update({key: value})
        else:
            super().__setattr__(key, value)

    def __repr__(self):
        return f'<OrderBook>([{self.market_time:%Y-%m-%d %H:%M:%S}] {self.ticker}, bid={self.best_bid_price}, ask={self.best_ask_price})'

    def __str__(self):
        return f'<OrderBook>([{self.market_time:%Y-%m-%d %H:%M:%S}] {self.ticker} {{Bid: {self.best_bid_price, self.best_bid_volume}, Ask: {self.best_ask_price, self.best_ask_volume}, Level: {self.max_level}}})'

    def __bool__(self):
        return bool(self.bid) and bool(self.ask)

    @classmethod
    def _parse_entry_name(cls, name: str, validate: bool = False) -> tuple[str, str, int]:
        if validate:
            if not re.match('^((bid_)|(ask_))((price_)|(volume_)|(order_))[0-9]+$', name):
                raise ValueError(f'Can not parse kwargs {name}.')

        side, key, level = name.split('_')
        level = int(level)

        return side, key, level

    @overload
    def parse(self, data: dict[str, float] = None, /, bid_price_1: float = math.nan, bid_volume_1: float = math.nan, ask_price_1: float = math.nan, ask_volume_1: float = math.nan, **kwargs: float):
        ...

    def parse(self, data: dict[str, float] = None, validate: bool = False, **kwargs):
        if not data:
            data = {}

        data.update(kwargs)

        for name, value in data.items():
            split_str = name.split('_')

            if validate:
                if len(split_str) != 3:
                    self.additional[name] = value

                side, key, level = name.split('_')

                if not (side == 'bid' or side == 'ask'):
                    self.additional[name] = value

                if not (key == 'price' or key == 'volume' or key == 'order'):
                    self.additional[name] = value

                if level.isnumeric():
                    level = int(level)
                else:
                    self.additional[name] = value
            else:
                side, key, level = name.split('_')
                level = int(level)

            book: list = self[side]

            if level <= 0:
                raise ValueError(f'Level of name [{name}] must be greater than zero!')

            if key == 'price':
                entry_idx = 0
            elif key == 'volume':
                entry_idx = 1
            elif key == 'order':
                entry_idx = 2
            else:
                raise ValueError(f'Can not parse kwargs {name}.')

            while level > len(book):
                book.append([float('nan'), 0, 0])

            book[level - 1][entry_idx] = value

    @classmethod
    def from_json(cls, json_message: str | bytes | bytearray | dict) -> OrderBook:
        if isinstance(json_message, dict):
            json_dict = json_message
        else:
            json_dict = json.loads(json_message)

        dtype = json_dict.pop('dtype', None)
        if dtype is not None and dtype != cls.__name__:
            raise TypeError(f'dtype mismatch, expect {cls.__name__}, got {dtype}.')

        self = cls(**json_dict)
        return self

    def to_list(self) -> list[float | int | str | bool]:
        min_length = min(len(self.bid), len(self.ask))
        r = ([self.__class__.__name__, self.ticker, self.timestamp]
             + [value for entry in self.bid[:min_length] for value in entry]
             + [value for entry in self.ask[:min_length] for value in entry])

        return r

    @classmethod
    def from_list(cls, data_list: list[float | int | str | bool]) -> OrderBook:
        dtype, ticker, timestamp = data_list[:3]
        bid_data, ask_data = np.array(data_list[3:]).reshape(2, -1).tolist()
        bid = np.array(bid_data).reshape(-1, 3).tolist()
        ask = np.array(ask_data).reshape(-1, 3).tolist()

        if dtype != cls.__name__:
            raise TypeError(f'dtype mismatch, expect {cls.__name__}, got {dtype}.')

        return cls(
            ticker=ticker,
            timestamp=timestamp,
            bid=bid,
            ask=ask
        )

    @property
    def market_price(self):
        return self.mid_price

    @property
    def mid_price(self):
        if np.isfinite(self.best_bid_price) and np.isfinite(self.best_ask_price):
            return (self.best_bid_price + self.best_ask_price) / 2
        else:
            return np.nan

    @property
    def spread(self):
        if np.isfinite(self.best_bid_price) and np.isfinite(self.best_ask_price):
            return self.best_ask_price - self.best_bid_price
        else:
            return np.nan

    @property
    def spread_pct(self):
        if self.mid_price != 0:
            return self.spread / self.mid_price
        else:
            return np.inf

    @property
    def bid(self) -> Book:
        book = self.Book(side=1)
        for price, volume, *_ in self['bid']:
            book.add(price=price, volume=volume)
        book.sort()
        return book

    @property
    def ask(self) -> Book:
        book = self.Book(side=-1)
        for price, volume, *_ in self['ask']:
            book.add(price=price, volume=volume)
        book.sort()
        return book

    @property
    def best_bid_price(self):
        if book := self.bid:
            return book[0][0]
        else:
            return np.nan

    @property
    def best_ask_price(self):
        if book := self.ask:
            return book[0][0]
        else:
            return np.nan

    @property
    def best_bid_volume(self):
        if book := self.bid:
            return book[0][1]
        else:
            return np.nan

    @property
    def best_ask_volume(self):
        if book := self.ask:
            return book[0][1]
        else:
            return np.nan


class BarData(MarketData):
    def __init__(
            self, *,
            ticker: str,
            timestamp: float,  # the bar end timestamp
            start_timestamp: float = None,
            bar_span: datetime.timedelta = None,
            high_price: float = math.nan,
            low_price: float = math.nan,
            open_price: float = math.nan,
            close_price: float = math.nan,
            volume: float = 0.,
            notional: float = 0.,
            trade_count: int = 0,
            **kwargs
    ):
        super().__init__(ticker=ticker, timestamp=timestamp, **kwargs)
        self.update(
            high_price=high_price,
            low_price=low_price,
            open_price=open_price,
            close_price=close_price,
            volume=volume,
            notional=notional,
            trade_count=trade_count
        )

        if bar_span is None and start_timestamp is None:
            raise ValueError('Must assign ether start_timestamp or bar_span or both.')
        elif start_timestamp is None:
            # self['start_timestamp'] = timestamp - bar_span.total_seconds()
            self['bar_span'] = bar_span.total_seconds()
        elif bar_span is None:
            self['start_timestamp'] = start_timestamp
            # self['bar_span'] = timestamp - start_timestamp
        else:
            self['start_timestamp'] = start_timestamp
            self['bar_span'] = bar_span.total_seconds()

    def __repr__(self):
        return f'<BarData>([{self.market_time:%Y-%m-%d %H:%M:%S}] {self.ticker}, open={self.open_price}, close={self.close_price}, high={self.high_price}, low={self.low_price})'

    @classmethod
    def from_json(cls, json_message: str | bytes | bytearray | dict) -> BarData:
        if isinstance(json_message, dict):
            json_dict = json_message
        else:
            json_dict = json.loads(json_message)

        dtype = json_dict.pop('dtype', None)
        if dtype is not None and dtype != cls.__name__:
            raise TypeError(f'dtype mismatch, expect {cls.__name__}, got {dtype}.')

        self = cls(**json_dict)
        return self

    def to_list(self) -> list[float | int | str | bool]:
        return [self.__class__.__name__,
                self.ticker,
                self.timestamp,
                self.high_price,
                self.low_price,
                self.open_price,
                self.close_price,
                self.get('start_timestamp'),
                self.get('bar_span'),
                self.volume,
                self.notional,
                self.trade_count]

    @classmethod
    def from_list(cls, data_list: list[float | int | str | bool]) -> BarData:
        (dtype, ticker, timestamp, high_price, low_price, open_price, close_price,
         start_timestamp, bar_span, volume, notional, trade_count) = data_list

        if dtype != cls.__name__:
            raise TypeError(f'dtype mismatch, expect {cls.__name__}, got {dtype}.')

        return cls(
            ticker=ticker,
            timestamp=timestamp,
            high_price=high_price,
            low_price=low_price,
            open_price=open_price,
            close_price=close_price,
            start_timestamp=start_timestamp if start_timestamp else None,
            bar_span=datetime.timedelta(bar_span) if bar_span else None,
            volume=volume,
            notional=notional,
            trade_count=trade_count
        )

    @property
    def high_price(self) -> float:
        return self['high_price']

    @property
    def low_price(self) -> float:
        return self['low_price']

    @property
    def open_price(self) -> float:
        return self['open_price']

    @property
    def close_price(self) -> float:
        return self['close_price']

    @property
    def bar_span(self) -> datetime.timedelta:
        if 'bar_span' in self:
            return datetime.timedelta(seconds=self['bar_span'])
        else:
            return datetime.timedelta(seconds=self['timestamp'] - self['start_timestamp'])

    @property
    def volume(self) -> float:
        return self['volume']

    @property
    def notional(self) -> float:
        return self['notional']

    @property
    def trade_count(self) -> int:
        return self['trade_count']

    @property
    def bar_start_time(self) -> datetime.datetime:
        if 'start_timestamp' in self:
            return datetime.datetime.fromtimestamp(self['start_timestamp'], tz=TIME_ZONE)
        else:
            return datetime.datetime.fromtimestamp(self['timestamp'] - self['bar_span'], tz=TIME_ZONE)

    @property
    def vwap(self) -> float:
        if self.volume != 0:
            return self.notional / self.volume
        else:
            LOGGER.warning(f'[{self.market_time}] {self.ticker} Volume data not available, using close_price as default VWAP value')
            return self.close_price

    @property
    def is_valid(self, verbose=False) -> bool:
        try:
            assert type(self.ticker) is str, '{} Invalid ticker'.format(str(self))
            assert np.isfinite(self.high_price), '{} Invalid high_price'.format(str(self))
            assert np.isfinite(self.low_price), '{} Invalid low_price'.format(str(self))
            assert np.isfinite(self.open_price), '{} Invalid open_price'.format(str(self))
            assert np.isfinite(self.close_price), '{} Invalid close_price'.format(str(self))
            assert np.isfinite(self.volume), '{} Invalid volume'.format(str(self))
            assert np.isfinite(self.notional), '{} Invalid notional'.format(str(self))
            assert np.isfinite(self.trade_count), '{} Invalid trade_count'.format(str(self))
            assert isinstance(self.bar_start_time, (datetime.datetime, datetime.date)), '{} Invalid bar_start_time'.format(str(self))
            assert isinstance(self.bar_span, datetime.timedelta), '{} Invalid bar_span'.format(str(self))

            return True
        except AssertionError as e:
            if verbose:
                LOGGER.warning(str(e))
            return False

    @property
    def market_price(self):
        """
        close price for a BarData
        :return: float
        """
        return self.close_price

    @property
    def bar_type(self):
        if self.bar_span > datetime.timedelta(days=1):
            return 'Over-Daily'
        elif self.bar_span == datetime.timedelta(days=1):
            return 'Daily'
        elif self.bar_span > datetime.timedelta(hours=1):
            return 'Over-Hourly'
        elif self.bar_span == datetime.timedelta(hours=1):
            return 'Hourly'
        elif self.bar_span > datetime.timedelta(minutes=1):
            return 'Over-Minute'
        elif self.bar_span == datetime.timedelta(minutes=1):
            return 'Minute'
        else:
            return 'Sub-Minute'

    @property
    def bar_end_time(self) -> datetime.datetime | datetime.date:
        if self.bar_type == 'Daily':
            return self.market_time.date()
        else:
            return self.market_time


class TickData(MarketData):
    def __init__(
            self, *,
            ticker: str,
            last_price: float,
            timestamp: float,
            bid_price: float = None,
            bid_volume: float = None,
            ask_price: float = None,
            ask_volume: float = None,
            order_book: OrderBook = None,
            total_traded_volume: float = 0.,
            total_traded_notional: float = 0.,
            total_trade_count: int = 0,
            **kwargs
    ):
        super().__init__(ticker=ticker, timestamp=timestamp, **kwargs)

        self.update(
            last_price=last_price,
            total_traded_volume=total_traded_volume,
            total_traded_notional=total_traded_notional,
            total_trade_count=total_trade_count,
        )

        if bid_price is not None:
            self['bid_price'] = bid_price

        if bid_volume is not None:
            self['bid_volume'] = bid_volume

        if ask_price is not None:
            self['ask_price'] = ask_price

        if ask_volume is not None:
            self['ask_volume'] = ask_volume

        if order_book is not None:
            self['order_book'] = order_book

        if kwargs:
            self['additional'] = dict(kwargs)

    @property
    def level_2(self) -> OrderBook | None:
        if 'order_book' in self:
            return OrderBook(**self['order_book'])
        else:
            return None

    @property
    def last_price(self) -> float:
        return self['last_price']

    @property
    def bid_price(self) -> float | None:
        return self.get('bid_price')

    @property
    def ask_price(self) -> float | None:
        return self.get('ask_price')

    @property
    def bid_volume(self) -> float | None:
        return self.get('bid_volume')

    @property
    def ask_volume(self) -> float | None:
        return self.get('ask_volume')

    @property
    def total_traded_volume(self) -> float:
        return self['total_traded_volume']

    @property
    def total_traded_notional(self) -> float:
        return self['total_traded_notional']

    @property
    def total_trade_count(self) -> float:
        return self['total_trade_count']

    def __repr__(self):
        return f'<TickData>([{self.market_time:%Y-%m-%d %H:%M:%S}] {self.ticker}, bid={self.bid_price}, ask={self.ask_price})'

    @classmethod
    def from_json(cls, json_message: str | bytes | bytearray | dict) -> TickData:
        if isinstance(json_message, dict):
            json_dict = json_message
        else:
            json_dict = json.loads(json_message)

        dtype = json_dict.pop('dtype', None)
        if dtype is not None and dtype != cls.__name__:
            raise TypeError(f'dtype mismatch, expect {cls.__name__}, got {dtype}.')

        self = cls(**json_dict)
        return self

    def to_list(self) -> list[float | int | str | bool]:
        """
        note that to_list WILL NOT retain orderbook info.
        to save all info, use to_json instead.
        """
        return [self.__class__.__name__,
                self.ticker,
                self.timestamp,
                self.last_price,
                self.bid_price,
                self.bid_volume,
                self.ask_price,
                self.ask_volume,
                self.total_traded_volume,
                self.total_traded_notional,
                self.total_trade_count]

    @classmethod
    def from_list(cls, data_list: list[float | int | str | bool]) -> TickData:
        (dtype, ticker, timestamp, last_price,
         bid_price, bid_volume, ask_price, ask_volume,
         total_traded_volume, total_traded_notional, total_trade_count) = data_list

        if dtype != cls.__name__:
            raise TypeError(f'dtype mismatch, expect {cls.__name__}, got {dtype}.')

        kwargs = {}

        if bid_price is not None:
            kwargs['bid_price'] = bid_price

        if ask_price is not None:
            kwargs['ask_price'] = ask_price

        if bid_volume is not None:
            kwargs['bid_volume'] = bid_volume

        if ask_volume is not None:
            kwargs['ask_volume'] = ask_volume

        return cls(
            ticker=ticker,
            timestamp=timestamp,
            last_price=last_price,
            total_traded_volume=total_traded_volume,
            total_traded_notional=total_traded_notional,
            total_trade_count=total_trade_count,
            **kwargs
        )

    @property
    def mid_price(self) -> float:
        return (self.bid_price + self.ask_price) / 2

    @property
    def market_price(self) -> float:
        return self.last_price


class TransactionData(MarketData):
    def __init__(
            self, *,
            ticker: str,
            price: float,
            volume: float,
            timestamp: float,
            side: int | float | str | TransactionSide = 0,
            multiplier: float = None,
            notional: float = None,
            transaction_id: str | int = None,
            buy_id: str | int = None,
            sell_id: str | int = None,
            **kwargs
    ):
        super().__init__(ticker=ticker, timestamp=timestamp, **kwargs)

        self['price'] = price
        self['volume'] = volume
        self['side'] = int(side) if isinstance(side, (int, float)) else TransactionSide(side).value

        if multiplier is not None:
            self['multiplier'] = multiplier

        if notional is not None:
            self['notional'] = notional

        if transaction_id is not None:
            self['transaction_id'] = transaction_id

        if buy_id is not None:
            self['buy_id'] = buy_id

        if sell_id is not None:
            self['sell_id'] = sell_id

    def __repr__(self):
        return f'<TransactionData>([{self.market_time:%Y-%m-%d %H:%M:%S}] {self.side.side_name} {self.ticker}, price={self.price}, volume={self.volume})'

    @classmethod
    def from_json(cls, json_message: str | bytes | bytearray | dict) -> TransactionData:
        if isinstance(json_message, dict):
            json_dict = json_message
        else:
            json_dict = json.loads(json_message)

        dtype = json_dict.pop('dtype', None)
        if dtype is not None and dtype != cls.__name__:
            raise TypeError(f'dtype mismatch, expect {cls.__name__}, got {dtype}.')

        self = cls(**json_dict)
        return self

    def to_list(self) -> list[float | int | str | bool]:
        return [self.__class__.__name__,
                self.ticker,
                self.timestamp,
                self.price,
                self.volume,
                self['side'],
                self.get('multiplier'),
                self.get('notional'),
                self.get('transaction_id'),
                self.get('buy_id'),
                self.get('sell_id')]

    @classmethod
    def from_list(cls, data_list: list[float | int | str | bool]) -> TransactionData:
        (dtype, ticker, timestamp, price, volume, side,
         multiplier, notional, transaction_id, buy_id, sell_id) = data_list

        if dtype != cls.__name__:
            raise TypeError(f'dtype mismatch, expect {cls.__name__}, got {dtype}.')

        kwargs = {}

        if multiplier is not None:
            kwargs['multiplier'] = multiplier

        if notional in kwargs:
            kwargs['notional'] = notional

        if transaction_id in kwargs:
            kwargs['transaction_id'] = transaction_id

        if buy_id in kwargs:
            kwargs['buy_id'] = buy_id

        if sell_id in kwargs:
            kwargs['sell_id'] = sell_id

        return cls(
            ticker=ticker,
            timestamp=timestamp,
            price=price,
            volume=volume,
            side=side,
            **kwargs
        )

    @classmethod
    def merge(cls, trade_data_list: list[TransactionData]) -> TransactionData | None:
        if not trade_data_list:
            return None

        ticker = trade_data_list[0].ticker
        assert all([trade.ticker == ticker for trade in trade_data_list]), 'input contains trade data of multiple ticker'
        timestamp = max([trade.timestamp for trade in trade_data_list])
        sum_volume = sum([trade.volume * trade.side.sign for trade in trade_data_list])
        sum_notional = sum([trade.notional * trade.side.sign for trade in trade_data_list])
        trade_side_sign = np.sign(sum_volume) if sum_volume != 0 else 1

        if sum_notional == 0:
            trade_price = 0
        elif sum_volume == 0:
            trade_price = np.nan
        else:
            trade_price = np.divide(sum_notional, sum_volume)

        trade_side = TransactionSide(trade_side_sign)
        trade_volume = abs(sum_volume)
        trade_notional = abs(sum_notional)

        merged_trade_data = cls(
            ticker=ticker,
            timestamp=timestamp,
            side=trade_side,
            price=trade_price,
            volume=trade_volume,
            notional=trade_notional
        )

        return merged_trade_data

    @property
    def price(self) -> float:
        return self['price']

    @property
    def volume(self) -> float:
        return self['volume']

    @property
    def side(self) -> TransactionSide:
        return TransactionSide(self['side'])

    @property
    def multiplier(self) -> float:
        return self.get('multiplier', 1.)

    @property
    def transaction_id(self) -> int | str | None:
        return self.get('transaction_id', None)

    @property
    def buy_id(self) -> int | str | None:
        return self.get('buy_id', None)

    @property
    def sell_id(self) -> int | str | None:
        return self.get('sell_id', None)

    @property
    def notional(self) -> float:
        return self.get('notional', self.price * self.volume * self.multiplier)

    @property
    def market_price(self) -> float:
        return self.price

    @property
    def flow(self):
        return self.side.sign * self.volume


class TradeData(TransactionData):
    def __init__(self, **kwargs):
        if 'trade_price' in kwargs:
            kwargs['price'] = kwargs.pop('trade_price')

        if 'trade_volume' in kwargs:
            kwargs['volume'] = kwargs.pop('trade_volume')

        super().__init__(**kwargs)

    @property
    def trade_price(self) -> float:
        return self['price']

    @property
    def trade_volume(self) -> float:
        return self['volume']

    @classmethod
    def from_json(cls, json_message: str | bytes | bytearray | dict) -> TradeData:
        return super(TradeData, cls).from_json(json_message=json_message)

    @classmethod
    def from_list(cls, data_list: list[float | int | str | bool]) -> TradeData:
        return super(TradeData, cls).from_list(data_list=data_list)
