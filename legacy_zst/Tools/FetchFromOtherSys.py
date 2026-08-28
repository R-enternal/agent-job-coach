import sys
sys.path.append('../..')
sys.path.append('.')
sys.path.append('./')
from Utils.FileReader import FileReader
import pandas as pd
from datetime import datetime

def fetch_data_from_external_systems(uuid=1001,info_dict={}):
    """根据传入的信息，从第三方系统中获取返回值

    Args:
        uuid (int): 用户ID，示例：{"uuid":"1001"}
        info_dict(json):从query中提取的时间，如：{"时间":"2025-01"}

    Returns:
        result: 查询到的信息，list格式，示例：result = [[1001, '蓝天科技', '戴尔OptiPlex 7080', '台式机', 6899, 5, 34495, '2023-01-05', '张伟', '银行转账'], [1002, '星辰网络', '华为MateStation B520', '台式机', 5299, 3, 15897, '2023-01-06', '李娜', '信用卡']]
    """
    # print(f'info_dict in fetch_data_from_external_systems():{info_dict}')
    result = None
    try:
        reader = FileReader()
        data = reader.read_csvs('data\query_from_others\query_data.csv')
        if "时间" in info_dict.keys():
            time = info_dict['时间']
            result = data[(data['用户ID']==uuid) & (data['时间']==time)]
        else:
            result = data[data['用户ID']==uuid]
    except Exception as e:
        print(f'从第三方系统获取信息出错:{e}')
    return result
