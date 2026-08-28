import os

from langchain_community.document_loaders import UnstructuredWordDocumentLoader,PyPDFLoader
import yaml
import pandas as pd

class FileReader:
    def __init__(self) -> None:
        pass
    def read_docx(self,file_path):
        loader = UnstructuredWordDocumentLoader(file_path)
        doc = loader.load_and_split()
        return doc

    def read_md(self,file_path):
        try:
            with open(file_path,'r',encoding='utf-8') as f:
                content = f.read()
                return content
        except FileNotFoundError:
            print(f'错误：文件{file_path}未找到')
            return None
        except Exception as e:
            print(f'读取文件时出错：{e}')
            return None
    
    def read_pdf(self,file_path):
        loader = PyPDFLoader(file_path)
        pages = loader.load_and_split()
        return pages

    def read_csvs(self,file_path):
        data = pd.read_csv(file_path)
        return data


class ConfigHandler:
    def __init__(self) -> None:
        pass   

    def read_yaml(self,file_path='Configs/rag_config.yaml',encoding='utf-8'):
        with open(file_path,'r',encoding=encoding) as f:
            return yaml.load(f.read(),Loader=yaml.FullLoader)
 
if __name__ == '__main__':
    reader = FileReader()
    config_reader = ConfigHandler()
    # config_yaml = config_reader.read_yaml(os.path.join(os.path.dirname(os.getcwd()),"Configs/rag_config.yml"))
    # print(os.path.dirname(os.getcwd()))
    model_conf = config_reader.read_yaml(os.path.join(os.path.dirname(os.getcwd()),"Configs/config.yml"))
    print(f">>> 读取模型配置：{model_conf}")
    # 查看模型名称
    print(f">>> model_name:{model_conf['model_name']}")
    # 查看Embedding模型名称
    print(f">>> embedding_name：{model_conf['embedding_name']}")
