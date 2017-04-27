# -*- coding: utf-8 -*-

import re
import pandas as pd
from WindAdapter.data_provider import WindDataProvider
from WindAdapter.enums import FreqType
from WindAdapter.enums import Header
from WindAdapter.enums import OutputFormat
from WindAdapter.enums import WindDataType
from WindAdapter.helper import WindQueryHelper
from WindAdapter.utils import py_assert

WIND_QUERY_HELPER = WindQueryHelper()
WIND_DATA_PROVIDER = WindDataProvider()


class FactorLoader:
    def __init__(self, start_date, end_date, factor_name, **kwargs):
        self._start_date = start_date
        self._end_date = end_date
        self._factor_name = factor_name
        self._sec_id = kwargs.get('sec_id', 'fulla')
        self._output_data_format = kwargs.get('output_data_format', OutputFormat.MULTI_INDEX_DF)
        self._save_file = kwargs.get('save_file', None)
        self._is_index = kwargs.get('is_index', True)

    @staticmethod
    def _merge_query_params(params, date=None):
        ret = ''
        for index, value in params.iteritems():
            if not pd.isnull(value):
                if index == 'tenor':
                    py_assert(date is not None, ValueError, 'date must given if tenor is not None')
                    unit = ''.join(re.findall('[0-9]+', params[Header.TENOR]))
                    freq = FreqType(params[Header.TENOR][len(unit):])
                    ret += 'startDate=' + WindDataProvider.advance_date(date, unit, freq).strftime(
                        '%Y%m%d') + ';endDate=' + date.strftime('%Y%m%d') + ';'
                else:
                    ret += (index + '=' + str(value) + ';')
        ret = ret[:-1]
        return ret

    def _get_sec_id(self, date):
        if isinstance(self._sec_id, basestring):
            sec_id = WIND_DATA_PROVIDER.get_universe(self._sec_id, date)
        elif isinstance(self._sec_id, list):
            sec_id = self._sec_id
        else:
            raise TypeError('FactorLoader._get_sec_id: sec_id must be either list of string')

        return sec_id

    def _retrieve_data(self, main_params, extra_params, output_data_format):
        output_data = pd.DataFrame()
        api = main_params[Header.API]
        if api == 'w.wsd':
            sec_id = WIND_DATA_PROVIDER.get_universe(self._sec_id, date=self._end_date) \
                if self._is_index else self._sec_id
            merged_extra_params = self._merge_query_params(extra_params)
            raw_data = WIND_DATA_PROVIDER.query_data(api=api,
                                                     sec_id=sec_id,
                                                     indicator=main_params[Header.INDICATOR],
                                                     extra_params=merged_extra_params,
                                                     start_date=self._start_date,
                                                     end_date=self._end_date)
            output_data = WIND_QUERY_HELPER.reformat_wind_data(raw_data=raw_data,
                                                               raw_data_type=WindDataType.WSD_TYPE,
                                                               output_data_format=output_data_format)
        elif api == 'w.wss':
            dates = WIND_DATA_PROVIDER.biz_days_list(start_date=self._start_date,
                                                     end_date=self._end_date,
                                                     freq=extra_params['period'])
            for date in dates:
                merged_extra_params = self._merge_query_params(extra_params, date=date)
                sec_id = WIND_DATA_PROVIDER.get_universe(self._sec_id, date=date)\
                    if self._is_index else self._sec_id
                raw_data = WIND_DATA_PROVIDER.query_data(api=api,
                                                         sec_id=sec_id,
                                                         indicator=main_params[Header.INDICATOR],
                                                         extra_params=merged_extra_params)

                tmp = WIND_QUERY_HELPER.reformat_wind_data(raw_data=raw_data,
                                                           raw_data_type=WindDataType.WSS_TYPE,
                                                           date=date,
                                                           output_data_format=output_data_format)
                output_data = pd.concat([output_data, tmp], axis=0)

        return output_data

    def load_data(self):
        main_params, extra_params = WIND_QUERY_HELPER.get_query_params(self._factor_name)
        ret = self._retrieve_data(main_params=main_params,
                                  extra_params=extra_params,
                                  output_data_format=self._output_data_format)

        return ret
