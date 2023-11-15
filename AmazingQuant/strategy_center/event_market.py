# -*- coding: utf-8 -*-

# ------------------------------
# @Time    : 2019/11/14
# @Author  : gao
# @File    : event_market.py.py
# @Project : AmazingQuant
# ------------------------------
from AmazingQuant.environment import Environment
from AmazingQuant.event_engine.event_engine_base import *
from AmazingQuant.data_center.api_data.get_kline import GetKlineData


class EventMarket(Event):
    current_close_price_all = None

    def __init__(self):
        super().__init__(event_type=EventType.EVENT_MARKET.value)

    @classmethod
    def update_position_frozen(cls, event):
        """
        每根bar运行前，更新今日持仓冻结数量
        :param event:
        :return:
        """
        if event.event_data_dict["strategy_data"].bar_index > 0:
            if Environment.bar_position_data_list:
                current_day = event.event_data_dict["strategy_data"].time_tag
                last_day = Environment.benchmark_index[event.event_data_dict["strategy_data"].bar_index - 1]
                for position_data in Environment.bar_position_data_list:
                    if last_day != current_day:
                        position_data['frozen'] = 0
                        # Environment.logger.info("更新今仓冻结数量")
        pass

    @classmethod
    def push_new_bar(cls, event):
        event.event_data_dict["strategy_data"].bar_index += 1

    @classmethod
    def update_market_data(cls, event):
        current_date = event.event_data_dict["strategy_data"].time_tag
        data_class = GetKlineData()
        stock_code_list = []
        # print(Environment.bar_position_data_list)
        for position_data in Environment.bar_position_data_list:
            stock_code_list.append(position_data['instrument'] + "." + position_data['exchange'])
        stock_code_list = list(set(stock_code_list))
        cls.current_close_price_all = data_class.get_market_data(Environment.daily_data, stock_code=stock_code_list,
                                                                 field=["close"], start=current_date, end=current_date)

    @classmethod
    def delete_position_zero(cls, event):
        """
        删除持仓数量为０的position
        :param event:
        :return:
        """
        Environment.bar_position_data_list = [position_data for position_data in Environment.bar_position_data_list if
                                              position_data['position'] != 0]
        pass

    @classmethod
    def update_position_close(cls, event):
        """
        更新bar_close持仓盈亏
        :param event:
        :return:
        """
        if Environment.bar_position_data_list:
            for position_data in Environment.bar_position_data_list:
                stock_code = position_data['instrument'] + "." + position_data['exchange']
                if isinstance(cls.current_close_price_all, float):
                    current_close_price = cls.current_close_price_all
                else:
                    current_close_price = cls.current_close_price_all["close"][stock_code]
                position_data['position_profit'] = position_data['position'] * (
                        current_close_price - position_data['average_price'])
                position_data['close'] = current_close_price
                position_data['hold_value'] = current_close_price * position_data['position']
        # Environment.logger.info("更新bar_close持仓盈亏")

    @classmethod
    def update_account_close(cls, event):
        """
        用bar_close更新总资产
        :param event:
        :return:
        """
        if Environment.bar_position_data_list:
            for account in Environment.bar_account_data_list:
                # 分资金账号update
                hold_balance = 0
                for position_data in Environment.bar_position_data_list:
                    if account['account_id'] == position_data['account_id']:
                        stock_code = position_data['instrument'] + "." + position_data['exchange']
                        if isinstance(cls.current_close_price_all, float):
                            current_close_price = cls.current_close_price_all
                        else:
                            current_close_price = cls.current_close_price_all["close"][stock_code]
                        hold_balance += position_data['position'] * current_close_price
                    account['total_balance'] = account['available'] + hold_balance
                pass
        # Environment.logger.info("更新bar_close总资产test0"*5,Environment.bar_account_data_list[0].total_balance)
        # Environment.logger.info("更新bar_close总资产test1" * 5, Environment.bar_account_data_list[1].total_balance)
