from abc import ABC,abstractmethod
from typing import Any,Dict,Optional
import json
from datetime import datetime

class VerboseHandler(ABC):
    """抽象基类，用于处理详细输出"""
    @abstractmethod
    def on_tool_start(self,tool_name:str,input_data:Any) -> None:
        pass

    @abstractmethod
    def on_tool_end(self,tool_name:str,output_data:Any,metadata:Optional[Dict]=None)->None:
        pass

    @abstractmethod
    def on_tool_error(self,tool_name:str,error:Exception) -> None:
        pass


class PrintHandler(VerboseHandler):
    """具体的详细输出处理器，将信息打印到控制台"""
    def __init__(self,verbose:bool=True,indent:int=2):
        self.verbose = verbose
        self.indent = indent

    def on_tool_start(self,tool_name:str,input_data:Any) -> None:
        if not self.verbose:
            return
        print(f"\n{'='*50}")
        print(f'工具开始执行：{tool_name}')
        print(f"时间：{datetime.now().isoformat()}")
        print("输入数据：")
        self._print_formatted(input_data)
        print(f"\n{'='*50}")

    def on_tool_end(self,tool_name:str,output_data:Any,metadata:Optional[Dict]=None) ->None:
        if not self.verbose:
            return
        print(f"\n{'=' * 50}")
        print(f'工具执行完成：{tool_name}')
        print(f"时间：{datetime.now().isoformat()}")
        print("输出数据：")
        self._print_formatted(output_data)
        if metadata:
            print("元数据：")
            self._print_formatted(metadata)
        print(f"\n{'=' * 50}")

    def on_tool_error(self,tool_name:str,error:Exception) -> None:
        if not self.verbose:
            return
        print(f"\n{'=' * 50}")
        print(f'工具执行出错：{tool_name}')
        print(f"时间：{datetime.now().isoformat()}")
        print(f"错误信息：{str(error)}")
        print(f"\n{'=' * 50}")

    def _print_formatted(self,data:Any) -> None:
        try:
            if isinstance(data,(dict,list)):
                formatted = json.dumps(data,indent=self.indent,ensure_ascii=False)
                print(formatted)
            else:
                print(str(data))
        except Exception as e:
            print(f"无法格式化输出：{e}")
            print(str(data))

class JsonFileHandler(VerboseHandler):
    """将详细输出保存到JSON文件"""
    def __init__(self,file_path):
        self.file_path = file_path
        self.logs = []

    def on_tool_start(self,tool_name:str,input_data:Any) -> None:
        log_entry = {
            "event":"tool_start",
            "tool_name":tool_name,
            "timestamp":datetime.now().isoformat(),
            "input_data":input_data
        }
        self.logs.append(log_entry)
        self._save_logs()

    def on_tool_end(self,tool_name:str,output_data:Any,metadata:Optional[Dict]=None) ->None:
        log_entry = {
            "event": "tool_end",
            "tool_name": tool_name,
            "timestamp": datetime.now().isoformat(),
            "output_data": output_data,
            "metadata": metadata or {}
        }
        self.logs.append(log_entry)
        self._save_logs()

    def on_tool_error(self,tool_name:str,error:Exception) -> None:
        log_entry = {
            "event": "tool_error",
            "tool_name": tool_name,
            "timestamp": datetime.now().isoformat(),
            "error": str(error)
        }
        self.logs.append(log_entry)
        self._save_logs()

    def _save_logs(self) -> None:
        """将日志保存到文件中"""
        with open(self.file_path,'w',encoding='utf-8') as f:
            json.dump(self.logs,f,indent=2,ensure_ascii=False)