import requests
import pandas as pd

if __name__=="__main__":
    try:
        rst = {"query":[],"answer":[]}
        # url = "http://172.20.10.2:8002/predict"
        url = "http://127.0.0.1:8002/predict"
        questions = ["这个扫地机器人能扫哪些地面？",
                     # "dToF导航技术是什么？",
                     # "app里面清洁记录作用是什么",
                     # "它能使用哪些语音助手",
                     # "HEPA 滤网要换吗？",
                     # "异常报警提示咋整？",
                     # "地毯多的家庭怎么使用",
                     # "要买高端机型吗？",
                     # "什么是自动集尘原理？",
                     # "太阳能充电扫地机器人能使用吗？",
                     # "拖地时怎么避免水渍？",
                     # "主刷要换吗",
                     # "怎么避免泄露家庭地图隐私？",
                     # "适合商业场所吗？",
                     # "跟洗地机相比效果怎样？",
                     # "耗电吗",
                     # "中国市场普及了吗",
                     # "机器人会自杀吗？"
                    ]
        # questions = ["根据我的扫地机器人的使用情况，生成一份使用报告,要2025年6月份的"]
        for question in questions:
            input_data = {"query":question,"uuid":1001}
            response = requests.post(url,json=input_data)
            response.raise_for_status()
            result = response.json()
            rst['query'].append(question)
            rst['answer'].append(result['answer'])
        print(rst)
        data = pd.DataFrame(rst)
        data.to_csv('Results/qwen3_20260130_all.csv',index=False)
    except Exception as e:
        print(e)