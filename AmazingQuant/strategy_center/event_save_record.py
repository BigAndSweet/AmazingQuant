# -*- coding: utf-8 -*-

# ------------------------------
# @Time    : 2019/11/14
# @Author  : gao
# @File    : event_save_record.py.py
# @Project : AmazingQuant
# ------------------------------

import copy

from AmazingQuant.environment import Environment
from AmazingQuant.event_engine.event_engine_base import *


class EventSaveRecord(Event):
    def __init__(self):
        super().__init__(event_type=EventType.EVENT_SAVE_RECORD.value)

    @classmethod
    def save_current_bar_data(cls, event):
        """
        记录每根bar的资金 持仓 委托　成交
        :param event:
        :return:
        """
        time_tag = event.event_data_dict["strategy_data"].time_tag
        Environment.order_data_dict[time_tag] = Environment.bar_order_data_list
        Environment.deal_data_dict[time_tag] = Environment.bar_deal_data_list
        Environment.position_data_dict[time_tag] = copy.deepcopy(Environment.bar_position_data_list)
        Environment.account_data_dict[time_tag] = copy.deepcopy(Environment.bar_account_data_list)
        Environment.logger.info("记录的资金、持仓、委托、成交", time_tag,)
