from Models.Factory import llm
import json
from tenacity import retry,stop_after_attempt,wait_fixed
import re



@retry(stop=stop_after_attempt(3),wait=wait_fixed(2))
def invoke_llm(prompt):
    return llm.invoke(prompt)

def extract_info(query):
    system_prompt = """
    你是一个优秀的信息提取专家，你的任务是从输入文本中获取时间这个参数值。
    返回JSON格式：{"时间":"2025-01"}.
    如果输入文本中没有相关参数，则返回空。
    举例如下：
    输入文本：使用2025年1月份的
    返回结果：{"时间":"2025-01"}
    输入文本：根据我的扫地机器人的使用情况，生成一份使用报告
    返回结果：{}
    """
    data = {}
    human_prompt = f"输入文本：{query},请返回提取的json。"
    prompt = [
        {
            "role":"system",
            "content":system_prompt
        },
        {
            "role":"user",
            "content":human_prompt
        }
    ]
    response = invoke_llm(prompt)
    if response:
        content = response.content
        match = re.search(r'\{.*\}', content)
        # print(f'match:{match}')
        print('----------------------------')
        if match:
            cleaned_json = match.group(0)
            print(f'cleaned_json:{cleaned_json},types:{type(cleaned_json)}')
            data = json.loads(cleaned_json)
        else:
            print("未找到有效的 JSON 数据！")
    return data


