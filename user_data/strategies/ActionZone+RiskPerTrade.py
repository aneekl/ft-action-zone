from datetime import datetime
from freqtrade.strategy import IStrategy, informative
from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter
from pandas import DataFrame
from freqtrade.persistence import Trade
from typing import Optional
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class ActionZoneRiskPerTrade(IStrategy):
    INTERFACE_VERSION = 3

    minimal_roi = {
        "0": 100
    }

    stoploss = -0.99

    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.088
    trailing_only_offset_is_reached = False

    process_only_new_candles = True
    startup_candle_count = 30
    use_custom_stoploss = False

    timeframe = '1d'
    risk_per_trade = 0.01 # risk 1% of portfolio per trade. 2% = 0.02 3% = 0.03

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            entry_tag: Optional[str], side: str, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        stop_price = last_candle['lowest'] * 0.98
        stop_to_percent = 1 - (stop_price / current_rate)
        wallet_percent = self.risk_per_trade / stop_to_percent
        new_stake = self.wallets.get_total_stake_amount() * wallet_percent

        return new_stake

    @property
    def protections(self):
        return  [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 0
            }
    ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        ema_fast = ta.EMA(dataframe, timeperiod=12)
        ema_slow = ta.EMA(dataframe, timeperiod=26)

        dataframe['ema_fast'] = ema_fast
        dataframe['ema_slow'] = ema_slow

        dataframe['lowest'] = dataframe['close'].rolling(26).min()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe['ema_fast'],dataframe['ema_slow']))
                & (dataframe["volume"] > 0)
            ),
            ['enter_long', 'enter_tag']] = (1, 'bought_while_green')

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe['ema_slow'],dataframe['ema_fast']))
                & (dataframe["volume"] > 0)
            ),
            ['exit_long', 'exit_tag']] = (1, 'sell_in_red')

        return dataframe
