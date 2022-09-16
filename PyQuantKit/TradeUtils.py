from __future__ import annotations

import copy
import datetime
import json
import uuid
from enum import Enum

from . import LOGGER
from .MarketUtils import TransactionSide, TradeData

LOGGER = LOGGER.getChild('TradeUtils')
__all__ = ['OrderState', 'OrderType', 'TradeInstruction', 'TradeReport']


class OrderType(Enum):
    UNKNOWN = -2
    CancelOrder = -1
    Manual = 0
    LimitOrder = 1
    LimitMarketMaking = 1.1
    MarketOrder = 2
    FOK = 2.1
    FAK = 2.2
    IOC = 2.3

    def __hash__(self):
        return self.value


class OrderState(Enum):
    UNKNOWN = -3
    Rejected = -2  # order rejected
    Invalid = -1  # invalid order
    Pending = 0  # order not sent. CAUTION pending order is not working nor done!
    Sent = 1  # order sent (to exchange)
    Placed = 2  # order placed in exchange
    PartFilled = 3  # order partial filled
    Filled = 4  # order fully filled
    Canceling = 5  # order canceling
    # PartCanceled = 5  # Deprecated
    Canceled = 6  # order stopped and canceled

    def __hash__(self):
        return self.value

    @property
    def is_working(self):
        """
        order in working status (ready to be filled),
        all non-working status are Pending / Filled / Cancelled / Rejected
        """
        if self.value == OrderState.Pending.value or \
                self.value == OrderState.Filled.value or \
                self.value == OrderState.Canceled.value or \
                self.value == OrderState.Invalid.value or \
                self.value == OrderState.Rejected.value:
            return False
        else:
            return True

    @property
    def is_done(self):
        if self.value == OrderState.Filled.value or \
                self.value == OrderState.Canceled.value or \
                self.value == OrderState.Rejected.value or \
                self.value == OrderState.Invalid.value:
            return True
        else:
            return False


class TradeReport(object):
    def __init__(
            self, *,
            ticker: str,
            side: int | float | str | TransactionSide,
            volume: float,
            notional: float,
            trade_time: datetime.datetime,
            order_id: str,
            price: float = None,
            trade_id: str = None,
            multiplier: float = 1,
            fee: float = .0
    ):
        """
        store trade report data
        :param ticker: ticker (symbol) of the given asset (stock, future, option, crypto and etc.)
        :param side: TransactionSide should be the same as TradeInstruction
        :param volume: Traded volume (the number of shares, contracts or crypto, etc.)
        :param notional: Traded notional (the amount of money) or premium of the option
        :param trade_time: datetime.datetime when trade was matched
        :param order_id: the id of its TradeInstruction
        :param price: the traded price. NOTED: trade price does not necessarily equal notional / volume. For example, currency swap, crypto swap (future) and debt
        :param trade_id: the id of itself
        :param multiplier: multiplier for contract or option
        :param fee: transition fee of this trade
        """
        assert volume >= 0, 'Trade volume must not be negative'

        self.__ticker = str(ticker)
        self.__side = TransactionSide(side)
        self.__price = price
        self.__volume = volume
        self.__notional = notional
        self.__trade_time = trade_time
        self.__order_id = str(order_id)
        self.__trade_id = str(trade_id) if trade_id is not None else str(uuid.uuid4())
        self.__multiplier = float(multiplier)
        self.__fee = fee

    def __repr__(self):
        return '<TradeReport>{}'.format({key: item.name if key == 'side' else item for key, item in self.__dict__.items()})

    def __eq__(self, other):
        if isinstance(other, TradeReport):
            return self.__repr__() == other.__repr__()
        else:
            return False

    def __str__(self):
        return f'<TradeReport>([{self.trade_time:%Y-%m-%d %H:%M:%S}] OrderID {self.order_id} {self.ticker} {self.side.name} {self.volume:.2f} @ {self.price:.2f} with trade_id {self.trade_id})'

    def __reduce__(self):
        return self.__class__.from_json, (self.to_json(),)

    def reset_order_id(self, order_id: str = None, **kwargs) -> TradeReport:
        """
        reset order_id id to given string
        :param order_id: new order id, use UUID by default
        :return:
        """
        if not kwargs.pop('_ignore_warning', False):
            LOGGER.warning('TradeReport OrderID being reset manually! TradeInstruction.reset_order_id() is the recommended method to do so.')

        if order_id is not None:
            self.__order_id = str(order_id)
        else:
            self.__order_id = str(uuid.uuid4())

        return self

    def reset_trade_id(self, trade_id: str = None) -> TradeReport:
        """
        reset trade id to given string
        :param trade_id:
        :return:
        """
        if trade_id is not None:
            self.__trade_id = str(trade_id)
        else:
            self.__trade_id = str(uuid.uuid4())

        return self

    def to_trade(self) -> TradeData:
        trade = TradeData(
            ticker=self.ticker,
            trade_time=self.trade_time,
            trade_price=self.notional / self.volume / self.multiplier if self.volume > 0 else 0,
            trade_volume=self.volume,
            side=self.side,
            multiplier=self.multiplier
        )
        return trade

    def to_json(self, fmt: str = 'str') -> str | dict:
        json_dict = {
            'ticker': self.__ticker,
            'side': self.__side.name,
            'price': self.__price,
            'volume': self.__volume,
            'notional': self.__notional,
            'trade_time': self.__trade_time.timestamp(),
            'order_id': self.__order_id,
            'trade_id': self.__trade_id,
            'multiplier': self.__multiplier,
            'fee': self.__fee,
        }

        if fmt == 'dict':
            return json_dict
        else:
            return json.dumps(json_dict)

    def copy(self, **kwargs):
        new_trade = self.__class__(
            ticker=kwargs.pop('ticker', self.__ticker),
            side=kwargs.pop('side', self.__side),
            volume=kwargs.pop('volume', self.__volume),
            notional=kwargs.pop('notional', self.__notional),
            trade_time=kwargs.pop('trade_time', self.__trade_time),
            order_id=kwargs.pop('order_id', None),
            price=kwargs.pop('price', self.__price),
            trade_id=kwargs.pop('trade_id', f'{self.__trade_id}.copy'),
            multiplier=kwargs.pop('multiplier', self.__multiplier),
            fee=kwargs.pop('fee', self.__fee)
        )

        return new_trade

    @classmethod
    def from_json(cls, json_message: str | bytes | bytearray | dict) -> TradeReport:
        if isinstance(json_message, dict):
            json_dict = json_message
        else:
            json_dict = json.loads(json_message)

        self = cls(
            ticker=json_dict['ticker'],
            side=TransactionSide(json_dict['side']),
            volume=json_dict['volume'],
            price=json_dict['price'],
            notional=json_dict['notional'],
            trade_time=datetime.datetime.fromtimestamp(json_dict['trade_time']),
            order_id=json_dict['order_id'],
            trade_id=json_dict['trade_id'],
            multiplier=json_dict['multiplier'],
            fee=json_dict['fee'],
        )

        return self

    @staticmethod
    def from_trade(trade_data: TradeData, order_id: str, trade_id: str = None) -> TradeReport:
        report = TradeReport(
            ticker=trade_data.ticker,
            side=trade_data.side,
            volume=trade_data.volume,
            notional=trade_data.notional,
            trade_time=trade_data.trade_time,
            order_id=order_id,
            trade_id=trade_id
        )
        return report

    @property
    def multiplier(self) -> float:
        return self.__multiplier

    @property
    def fee(self) -> float:
        return self.__fee

    @property
    def ticker(self) -> str:
        return self.__ticker

    @property
    def side(self) -> TransactionSide:
        return self.__side

    @property
    def volume(self) -> float:
        return self.__volume

    @property
    def notional(self) -> float:
        return self.__notional

    @property
    def price(self) -> float:
        if self.__price is not None:
            return self.__price
        elif self.__volume == 0:
            return .0
        else:
            return self.__notional / self.__volume / self.__multiplier

    @property
    def trade_time(self) -> datetime.datetime:
        return self.__trade_time

    @property
    def timestamp(self):
        return self.__trade_time.timestamp()

    @property
    def order_id(self) -> str:
        return self.__order_id

    @property
    def trade_id(self) -> str:
        return self.__trade_id


class TradeInstruction(object):
    def __init__(
            self, *,
            ticker: str,
            side: int | float | str | TransactionSide,
            order_type: OrderType = OrderType.Manual,
            volume: float = 0.0,
            limit_price: float = None,
            order_id: str = None,
            multiplier: float = 1
    ):
        if volume <= 0:
            raise ValueError(f'Invalid trade volume {volume}!')

        self.__ticker = str(ticker)
        self.__side = TransactionSide(side)
        self.__order_type = order_type
        self.__volume = float(volume)
        self.__limit_price = limit_price
        self.__order_id = str(order_id) if order_id is not None else str(uuid.uuid4())
        self.__multiplier = float(multiplier)

        self.__order_state: OrderState = OrderState.Pending
        self.__filled_volume: float = 0.0
        self.__filled_notional: float = 0.0
        self.__fee = .0
        self.__start_datetime: datetime.datetime | None = None
        self.__cancel_datetime: datetime.datetime | None = None
        self.__finish_datetime: datetime.datetime | None = None
        self.__trades: dict[str, TradeReport] = {}

    def __repr__(self):
        return '<TradeInstruction>{}'.format(self.__dict__)

    def __eq__(self, other):
        if isinstance(other, TradeInstruction):
            return self.__repr__() == other.__repr__()
        else:
            return False

    def __str__(self):
        if self.limit_price is None or self.order_type == OrderType.MarketOrder:
            return f'<TradeInstruction>({self.order_type.name} OrderID {self.order_id} {self.side.name} {self.ticker} {self.volume:.2f} filled {self.filled_volume:.2f} @ {self.average_price:.2f} now {self.order_state.name})'
        else:
            return f'<TradeInstruction>({self.order_type.name} OrderID {self.order_id} {self.side.name} {self.ticker} {self.volume:.2f} limit {self.limit_price:.2f} filled {self.filled_volume:.2f} @ {self.average_price:.2f} now {self.order_state.name})'

    def __reduce__(self):
        return self.__class__.from_json, (self.to_json(),)

    def reset(self):
        self.__trades = {}

        self.__order_state: OrderState = OrderState.Pending
        self.__filled_volume: float = 0.0
        self.__filled_notional: float = 0.0
        self.__fee = .0
        self.__start_datetime: datetime.datetime | None = None
        self.__cancel_datetime: datetime.datetime | None = None
        self.__finish_datetime: datetime.datetime | None = None
        self.__trades: dict[str, TradeReport] = {}

    def reset_order_id(self, order_id: str = None, **kwargs) -> TradeInstruction:
        """
        reset order id to given string
        :param order_id:
        :return:
        """
        if not kwargs.pop('_ignore_warning', False):
            LOGGER.warning('TradeInstruction OrderID being reset manually! Position.reset_order_id() is the recommended method to do so.')

        if order_id is not None:
            self.__order_id = str(order_id)
        else:
            self.__order_id = str(uuid.uuid4())

        for trade_report in self.__trades.values():
            trade_report.reset_order_id(order_id=self.__order_id, _ignore_warning=True)

        return self

    def set_order_state(self, order_state: OrderState, market_datetime: datetime.datetime = datetime.datetime.utcnow()) -> TradeInstruction:
        self.__order_state = order_state

        # assign a start_datetime if order placed
        if order_state == OrderState.Placed:
            self.__start_datetime = market_datetime

        if order_state == OrderState.Canceled:
            self.__cancel_datetime = market_datetime
            self.__finish_datetime = market_datetime

        return self

    def fill(self, trade_report: TradeReport) -> TradeInstruction:
        if trade_report.order_id != self.order_id:
            LOGGER.warning(f'Order ID not match! Instruction ID {self.order_id}; Report ID {trade_report.order_id}')
            return self

        if trade_report.trade_id in self.trades:
            LOGGER.warning('Duplicated trade received! Instruction {}; Report {}'.format(str(self), str(trade_report)))
            return self

        if trade_report.volume != 0:
            # update multiplier
            if len(self.__trades) > 0:
                assert self.__multiplier == trade_report.multiplier, 'Multiplier not match!'
            else:
                self.__multiplier = trade_report.multiplier

            if trade_report.volume + self.__filled_volume > self.__volume:
                LOGGER.warning('Fatal error!\nTradeInstruction: \n\t{}\nTradeReport:\n\t{}'.format(str(TradeInstruction), '\n\t'.join([str(x) for x in self.__trades.values()])))
                raise ValueError('Fatal error! trade reports filled volume exceed order volume!')

            self.__filled_volume += abs(trade_report.volume)
            self.__filled_notional += abs(trade_report.notional)

        if self.__filled_volume == self.__volume:
            self.set_order_state(OrderState.Filled)
            self.__finish_datetime = trade_report.trade_time
        elif self.__filled_volume > 0:
            self.set_order_state(OrderState.PartFilled)

        self.__trades[trade_report.trade_id] = trade_report

        return self

    def cancel_order(self) -> TradeInstruction:
        self.set_order_state(OrderState.Canceling)

        cancel_instruction = copy.copy(self)
        cancel_instruction.__order_type = OrderType.CancelOrder

        return cancel_instruction

    def canceled(self, canceled_datetime: datetime.datetime) -> TradeInstruction:
        LOGGER.warning(DeprecationWarning('[canceled] depreciated! Use [set_order_state] instead!'), stacklevel=2)

        self.set_order_state(OrderState.Canceled, canceled_datetime)
        return self

    def to_json(self, with_trade=True, fmt: str = 'str') -> str | dict:
        json_dict = {
            'ticker': self.__ticker,
            'side': self.__side.name,
            'order_type': self.__order_type.name,
            'volume': self.__volume,
            'limit_price': self.__limit_price,
            'order_id': self.__order_id,
            'multiplier': self.__multiplier,
            'order_state': self.__order_state.name,
            'filled_volume': self.__filled_volume,
            'filled_notional': self.__filled_notional,
            'fee': self.__fee,
            'start_datetime': None if self.__start_datetime is None else self.__start_datetime.timestamp(),
            'cancel_datetime': None if self.__cancel_datetime is None else self.__cancel_datetime.timestamp(),
            'finish_datetime': None if self.__finish_datetime is None else self.__finish_datetime.timestamp(),
            'trades': {_: self.__trades[_].to_json(fmt='dict') for _ in self.__trades} if with_trade else {},
        }

        if fmt == 'dict':
            return json_dict
        else:
            return json.dumps(json_dict)

    @classmethod
    def from_json(cls, json_message: str | bytes | bytearray | dict) -> TradeInstruction:
        if isinstance(json_message, dict):
            json_dict = json_message
        else:
            json_dict = json.loads(json_message)

        self = cls(
            ticker=json_dict['ticker'],
            side=TransactionSide(json_dict['side']),
            order_type=OrderType[json_dict['order_type']],
            volume=json_dict['volume'],
            limit_price=json_dict['limit_price'],
            order_id=json_dict['order_id'],
            multiplier=json_dict['multiplier']
        )

        self.__order_state = OrderState[json_dict['order_state']]
        self.__filled_volume = json_dict['filled_volume']
        self.__filled_notional = json_dict['filled_notional']
        self.__fee = json_dict['fee']
        self.__start_datetime = None if json_dict['start_datetime'] is None else datetime.datetime.fromtimestamp(json_dict['start_datetime'])
        self.__cancel_datetime = None if json_dict['cancel_datetime'] is None else datetime.datetime.fromtimestamp(json_dict['cancel_datetime'])
        self.__finish_datetime = None if json_dict['finish_datetime'] is None else datetime.datetime.fromtimestamp(json_dict['finish_datetime'])

        for trade_id in json_dict['trades']:
            trade_json = json_dict['trades'][trade_id]
            report = TradeReport.from_json(trade_json)
            self.__trades[report.trade_id] = report

        return self

    @property
    def fee(self):
        return self.__fee

    @fee.setter
    def fee(self, value):
        self.__fee = float(value)

    @property
    def is_working(self):
        return self.__order_state.is_working

    @property
    def is_done(self):
        return self.__order_state.is_done

    @property
    def order_id(self) -> str:
        return self.__order_id

    @property
    def ticker(self) -> str:
        return self.__ticker

    @property
    def side(self) -> TransactionSide:
        return self.__side

    @property
    def order_type(self) -> OrderType:
        return self.__order_type

    @property
    def volume(self) -> float:
        return self.__volume

    @property
    def limit_price(self) -> float | None:
        return self.__limit_price

    @property
    def start_time(self) -> datetime.datetime | None:
        return self.__start_datetime

    @property
    def cancel_time(self) -> datetime.datetime | None:
        return self.__cancel_datetime

    @property
    def finish_time(self) -> datetime.datetime | None:
        return self.__finish_datetime

    @property
    def order_state(self) -> OrderState:
        return self.__order_state

    @property
    def filled_volume(self) -> float:
        return self.__filled_volume

    @property
    def working_volume(self) -> float:
        return self.__volume - self.__filled_volume

    @property
    def filled_notional(self) -> float:
        return self.__filled_notional

    @property
    def average_price(self) -> float:
        if self.__filled_volume != 0:
            return self.__filled_notional / self.__filled_volume / self.__multiplier
        else:
            return float('NaN')

    @property
    def trades(self) -> dict[str, TradeReport]:
        return self.__trades

    @property
    def multiplier(self) -> float:
        return self.__multiplier
