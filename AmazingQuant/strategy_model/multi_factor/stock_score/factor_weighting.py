
# -*- coding: utf-8 -*-

# ------------------------------
# @Time    : 2020/3/31
# @Author  : gao
# @File    : factor_weighting.py
# @Project : AmazingQuant
# ------------------------------
"""
因子加权方法
(1)等权法
(2)历史信息比例(IR)加权法
(3)历史收益率加权法,均值和半衰
(4)历史IC加权法,均值和半衰
(5)最大化IC_IR加权法，未实现
(6)最大化IC加权法，未实现
"""
from datetime import datetime

import pandas as pd
import numpy as np

from AmazingQuant.constant import LocalDataFolderName
from AmazingQuant.config.local_data_path import LocalDataPath
from AmazingQuant.utils.get_data import get_local_data
from AmazingQuant.constant import DatabaseName
from AmazingQuant.utils.mongo_connection_me import MongoConnect
from apps.server.database_server.database_field.field_multi_factor import FactorRegressionAnalysisResult, \
    FactorIcAnalysisResult


class FactorWeighting(object):
    def __init__(self, factor_data):
        # 因子数据
        self.factor_data = factor_data
        # 因子加权后的结果
        self.factor_data_weighted = None

    def weighting(self, weight_method='equal', weight_normalization=True, **weight_para):
        """
        :param weight_normalization: 权重标准化
        :param weight_para:
        :param weight_method:
            'equal'，等权法，weight_para: data=factor_return
            'return_mean'， 历史收益率加权法，平均值，window是平均值周期, weight_para: data=factor_return, window=20
            'return_half_life'，历史收益率加权法，半衰期法，half_life是半衰期, weight_para: data=factor_return, half_life=20
            'return_ir'，  历史因子收益率信息比例(IR)加权法，window是平均值周期, weight_para: data=factor_return, window=20

            'ic_mean'， rank_ic加权法，平均值，window是平均值周期, weight_para: data=factor_ic, window=20
            'ric_half_life'，rank_ic加权法加权法，半衰期法，half_life是半衰期, weight_para: data=factor_ic, half_life=20

        :return:
        """
        factor_single_weight_dict = {}
        factor_total_weight = None
        if weight_method == 'max_ic_ir':
            factor_single_weight_dict = dict(self.weighting_max_ic_ir(factor_ic=weight_para['data'],
                                                                         window=weight_para['window']))
        else:

            for factor_name in weight_para['data']:
                factor_single_weight_dict[factor_name] = None
                if weight_method == 'equal':
                    factor_single_weight_dict[factor_name] = 1
                elif weight_method == 'return_mean':
                    factor_single_weight_dict[factor_name] = self.weighting_return_mean(factor_name, data=weight_para['data'],
                                                                                   window=weight_para['window'])
                elif weight_method == 'return_half_life':
                    factor_single_weight_dict[factor_name] = self.weighting_return_half_life(factor_name, data=weight_para['data'],
                                                                                        half_life=weight_para['half_life'])
                elif weight_method == 'return_ir':
                    factor_single_weight_dict[factor_name] = self.weighting_return_ir(factor_name, data=weight_para['data'],
                                                                                 window=weight_para['window'])
                elif weight_method == 'ic_mean':
                    factor_single_weight_dict[factor_name] = self.weighting_ic_mean(factor_name, data=weight_para['data'],
                                                                               window=weight_para['window'])
                elif weight_method == 'ic_half_life':
                    factor_single_weight_dict[factor_name] = self.weighting_ic_half_life(factor_name, data=weight_para['data'],
                                                                                    half_life=weight_para['half_life'])
                else:
                    raise Exception('weight_method is not exist')

        for factor_name in factor_single_weight_dict:
            if factor_total_weight is None:
                factor_total_weight = factor_single_weight_dict[factor_name]
            else:
                factor_total_weight = factor_total_weight + factor_single_weight_dict[factor_name]

        for factor_name in self.factor_data:
            factor_single_data_weighted = self.factor_data[factor_name].mul(
                factor_single_weight_dict[factor_name] / factor_total_weight, axis=0)
            if self.factor_data_weighted is None:
                self.factor_data_weighted = factor_single_data_weighted
            else:
                self.factor_data_weighted = self.factor_data_weighted + factor_single_data_weighted
        if weight_normalization:
            self.factor_data_weighted = self.factor_data_weighted.sub(self.factor_data_weighted.min(axis=1), axis=0).\
                div(self.factor_data_weighted.max(axis=1) - self.factor_data_weighted.min(axis=1), axis=0)
        return self.factor_data_weighted.div(self.factor_data_weighted.sum(axis=1), axis=0)

    @staticmethod
    def weighting_equal():
        return 1

    @staticmethod
    def weighting_return_mean(factor_name, **weight_para):
        return weight_para['data'][factor_name]['daily'].rolling(window=weight_para['window']).mean()

    @staticmethod
    def weighting_return_half_life(factor_name, **weight_para):
        return weight_para['data'][factor_name]['daily'].ewm(halflife=weight_para['half_life'], adjust=False).mean()

    @staticmethod
    def weighting_return_ir(factor_name, **weight_para):
        return weight_para['data'][factor_name]['daily'].rolling(window=weight_para['window']).mean() / \
               weight_para['data'][factor_name]['daily'].rolling(window=weight_para['window']).std()

    @staticmethod
    def weighting_ic_mean(factor_name, **weight_para):
        return weight_para['data'][factor_name]['delay_1'].rolling(window=weight_para['window']).mean()

    @staticmethod
    def weighting_ic_half_life(factor_name, **weight_para):
        return weight_para['data'][factor_name]['delay_1'].ewm(halflife=weight_para['half_life'], adjust=False).mean()

    @staticmethod
    def weighting_max_ic_ir(factor_ic, **weight_para):
        window = weight_para['window']
        factor_ic_all = pd.DataFrame(columns=list(factor_ic.keys()))
        for factor_name in factor_ic.keys():
            factor_ic_all[factor_name] = factor_ic[factor_name]['delay_1']
        factor_ic_mean = factor_ic_all.rolling(window=window).mean()
        factor_ic_cov = factor_ic_all.rolling(window=window).cov()

        def cal_weight(mean_value, factor_ic_cov):
            ic = factor_ic_cov.loc[(mean_value.name, )]
            return np.array(np.mat(ic.values).I * np.mat(mean_value.values.reshape(1, -1).T)).T[0]

        result = factor_ic_mean.apply(cal_weight, args=(factor_ic_cov,), axis=1, result_type="expand")
        result.columns = factor_ic.keys()
        return result.div(result.sum(1), axis=0)


if __name__ == '__main__':
    factor_list = ['factor_ma5', 'factor_ma10']

    path = LocalDataPath.path + LocalDataFolderName.FACTOR.value + '/'
    factor_data = {}
    for factor_name in factor_list:
        factor_single_data = get_local_data(path, factor_name + '.h5')
        # 指数数据不全，需要删一部分因子数据
        factor_data[factor_name] = factor_single_data[factor_single_data.index < datetime(2020, 1, 1)]

    with MongoConnect(DatabaseName.MULTI_FACTOR_DATA.value):
        factor_ic = {}
        factor_return = {}
        for factor_name in factor_list:
            factor_regression_analysis_result = FactorRegressionAnalysisResult.objects(factor_name=factor_name) \
                .only('factor_name') \
                .only('begin_date') \
                .only('end_date') \
                .only('factor_return') \
                .as_pymongo()
            factor_return[factor_name] = pd.DataFrame(factor_regression_analysis_result[0]['factor_return'])
            factor_return[factor_name].index = pd.DatetimeIndex(factor_return[factor_name].index)

            factor_ic_result = FactorIcAnalysisResult.objects(factor_name=factor_name) \
                .only('factor_name') \
                .only('begin_date') \
                .only('end_date') \
                .only('ic') \
                .as_pymongo()
            # print(factor_ic_result)
            factor_ic[factor_name] = pd.DataFrame(factor_ic_result[0]['ic'])
            factor_ic[factor_name].index = pd.DatetimeIndex(factor_ic[factor_name].index)

    factor_weighting_obj = FactorWeighting(factor_data)
    # factor_weighted = factor_weighting_obj.weighting(weight_method='return_half_life', data=factor_return, half_life=5)
    factor_weighted = factor_weighting_obj.weighting(weight_method='max_ic_ir', data=factor_ic, window=20)
