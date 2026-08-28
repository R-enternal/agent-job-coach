
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
import os
import sys
sys.path.append('../..')
sys.path.append('.')
sys.path.append('./')
sys.path.append(os.path.dirname(os.getcwd()))
# print(sys.path)
from Models.Factory import llm
from .ExtractInfo import extract_info
from .FetchFromOtherSys import fetch_data_from_external_systems
from Utils.FileReader import ConfigHandler

config_reader = ConfigHandler()
model_conf = config_reader.read_yaml(os.path.join(os.getcwd(),"Configs/config.yml"))
# model_conf = config_reader.read_yaml("Configs/config.yml")

def generator(query,uuid=1001,verbose=False):
    try:
        prompt = []
        # print(model_conf.keys())
        with open(model_conf['reporter_prompt_path'],'r',encoding='utf-8') as f:
            for line in f:
                prompt.append(line)

        report_para = extract_info(query)
        if not isinstance(report_para,dict):
            return f"信息提取返回结果格式不对，请检查,返回信息为：{report_para}"
        print(f'report_para in generator:{report_para}')
        information = fetch_data_from_external_systems(uuid,report_para)
        if information is None:
            return ""
        print(f'inpormation in generator:{information}')
        template = PromptTemplate(
            template="".join(prompt),
            input_variables=["INFORMATION"]
        )
        print(f'template in generator:{template}')
        formatted_prompt = template.format(INFORMATION=information)
        print(f'formatted_prompt in generator:{formatted_prompt}')
        final_template = PromptTemplate.from_template(formatted_prompt)
        print(f'final_template in generator:{final_template}')

        chain = {"query":RunnablePassthrough()} | final_template | llm | StrOutputParser()
        answer = chain.invoke(query)
        print(f'answer in generator:{answer}')
        return answer
    except Exception as e:
        print(e)
        return None
