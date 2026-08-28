import os
import re
import json
from typing import List, Optional, Tuple

import pandas as pd
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser,JsonOutputToolsParser
from langchain.schema.output_parser import StrOutputParser
from langchain.tools.base import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import render_text_description
from pydantic import ValidationError
from langchain_core.prompts import HumanMessagePromptTemplate

from Agent.Action import Action


class ReActAgent:
    @staticmethod
    def extract_json_from_action_rst(text: str) -> str | None:
        """
        从RST格式文本中提取JSON代码块内容
        该函数使用正则表达式匹配文本中的json代码块，并返回最后一个匹配到的JSON字符串。
        参数:
            text (str): 包含RST格式的输入文本，可能包含代码块
        返回值:
            str | None: 如果找到JSON代码块则返回其中的内容（不包括json和标记），
                       如果没有找到则返回None
        """
        # 使用正则表达式匹配json代码块
        pattern = re.compile(r'```json(.*?)```', flags=re.DOTALL)
        matches = pattern.findall(text)
        if matches:
            json_str = matches[-1]
            return json_str
        return None

    @staticmethod
    def format_observations(response: str, action: Action, observation: str) -> str:
        """
        格式化观察结果，去除响应中的JSON代码块，并将动作和观察结果追加到响应末尾
        参数:
            response (str): 原始响应字符串，可能包含JSON代码块
            action (Action): 执行的动作对象
            observation (str): 动作执行后的观察结果
        返回值:
            str: 格式化后的字符串，包含清理后的响应内容、动作信息和观察结果
        """
        rst = re.sub(r"```json(.*?)```", "", response, flags=re.DOTALL)
        rst += "\n" + str(action) + "\n返回结果为：\n" + observation
        return rst

    def __init__(self, llm: BaseChatModel, tools: List[BaseTool], main_prompt_file_path: str):
        """
        初始化智能体构造器
        参数:
            llm (BaseChatModel): 基础聊天模型实例
            tools (List[BaseTool]): 可用工具列表
            main_prompt_file_path (str): 主提示词文件路径
        """
        self.llm = llm
        self.tools = tools

        self.output_parser = PydanticOutputParser(pydantic_object=Action)
        try:
            self.robust_parser = OutputFixingParser.from_llm(
                parser=self.output_parser,
                llm=llm
            )
        except Exception as e:
            print(f"不能修复的输出. 错误: {e}")
            print("请尝试提升提示词质量或者使用一个更加合适的大模型")
        self.main_prompt_file_path = main_prompt_file_path

        self.__init_prompts()
        self.__init_chains()

    def __init_prompts(self):
        """
        初始化提示模板
        该方法从指定文件路径读取主提示内容，并构建聊天提示模板。
        模板包含聊天历史占位符和人类消息模板，同时将工具信息、工具名称列表
        和输出格式指令作为部分参数绑定到模板中。
        """
        with open(os.path.join(os.getcwd(), self.main_prompt_file_path), 'r', encoding='utf-8') as f:
            self.prompt = ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template(f.read()), ]).partial(
                tools=render_text_description(self.tools),
                tool_names=",".join([tool.name for tool in self.tools]),
                format_instructions=self.output_parser.get_format_instructions())

    def __init_chains(self):
        """
        初始化主链对象
        该方法创建一个由提示词、语言模型和字符串输出解析器组成的处理链，
        用于处理输入并生成相应的文本输出。
        """
        self.main_chains = (self.prompt | self.llm | StrOutputParser())

    def confirm_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        根据工具名称查找并返回对应的工具对象
        参数:
            tool_name (str): 要查找的工具名称
        返回值:
            Optional[BaseTool]: 如果找到匹配的工具则返回该工具对象，否则返回None
        """
        # print(f'confirm_tool:{tool_name}')
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def step_by_step(
        self, task, short_term_memory=None, chat_history=None, verbose=False
    ) -> Tuple[Optional[Action], str]:
        """
        执行逐步任务处理，将任务分解为多个步骤并生成相应的动作和响应
        参数:
            task (str): 需要处理的任务描述
            short_term_memory (list, optional): 短期记忆列表，包含之前的执行步骤
            chat_history (object, optional): 聊天历史对象，包含对话记录
            verbose (bool): 是否启用详细输出模式
        返回值:
            Tuple[Action, str]: 返回一个元组，包含解析后的动作对象和完整的响应字符串
        """
        inputs = {
            "input": task,
            "agent_scratchpad": "\n".join(short_term_memory),
            "chat_history": chat_history.messages if chat_history else chat_history,
        }
        response = ""
        for s in self.main_chains.stream(inputs):
            response += s
        print(f'response:{response}')
        action = self._parse_action(response)
        print(f'action:{action}')
        return action, response

    def exec_actions(self, action: Action) -> str:
        """
        执行指定的动作并返回观察结果
        参数:
            action (Action): 要执行的动作对象，包含工具名称和参数
        返回值:
            str: 动作执行后的观察结果或错误信息
        """
        # print(f'action in exec_actions:{action}, action tool_name in exec_actions:{action.tool_name}')
        tool = self.confirm_tool(action.tool_name)
        # print(f'tool in exec_actions:{tool}')
        if tool is None:
            observation = (
                f"Error:没找到待执行的工具或者指令 '{action.tool_name}'."
                f"请从提供的工具或者指令列表中选择，注意按对顶格式输出内容。"
            )
        else:
            try:
                print(f'tool 执行：{action.args}')
                observation = tool.run(action.args)
                print(f'tool执行结果：{observation}')
            except ValidationError as e:
                observation = (
                    f"执行动作时参数有非法错误 in exec_actions：{str(e)},args:{action.args}"
                )
                print(f'action in exec_actions:{action.args}')
            except Exception as e:
                observation = f"Error in exec_actions:{str(e)},{type(e).__name__},args:{action.args}"
        return observation

    def _parse_action(self, response: str) -> Optional[Action]:
        """从模型响应中稳健解析 Action（提取 JSON 代码块 + Pydantic 校验 + 自愈修复）"""
        action_rst_json = self.extract_json_from_action_rst(response)
        try:
            if isinstance(action_rst_json, dict):
                return self.robust_parser.parse(action_rst_json)
            if action_rst_json:
                return self.robust_parser.parse(action_rst_json)
            return self.robust_parser.parse(response)
        except Exception as exc:  # 解析失败：交给调用方作为观察让模型重试
            print(f"[ReAct] 动作解析失败: {exc}")
            return None

    def execute(
        self,
        task: str,
        uuid: int,
        chat_history: ChatMessageHistory,
        verbose: bool = False,
        max_steps: int = 6,
    ) -> str:
        """
        执行任务的主要方法
        参数:
            task (str): 需要执行的任务描述
            uuid (int): 任务的唯一标识符
            chat_history (ChatMessageHistory): 聊天历史记录对象
            verbose (bool): 是否启用详细输出模式，默认为False
            max_steps (int): 推理-行动循环的最大步数（对标仓维云 agent_max_steps）
        返回值:
            str: 执行任务后得到的答案
        """
        short_term_memory = []
        # 防死循环：记录已执行过的 (tool_name, args)，重复调用时直接采用上次观察
        executed: dict[str, str] = {}
        answer = ""
        for step in range(1, max_steps + 1):
            print(f"\n[ReAct] ====== 第 {step}/{max_steps} 步 ======")
            action, response = self.step_by_step(
                task=task,
                short_term_memory=short_term_memory,
                chat_history=chat_history,
                verbose=verbose,
            )
            if action is None:
                # 动作解析失败：把错误作为观察回填，让模型重试（对标仓维云自愈思路）
                observation = "Error: 模型输出无法解析为合法动作 JSON，请严格按 ```json 格式重新输出动作。"
                short_term_memory.append(self.format_observations(response, None, observation))
                continue

            # 最终答案动作：直接返回
            if action.tool_name == "Final Answer":
                args = action.args or {}
                answer = args.get("answer", "") or str(args)
                print(f"[ReAct] 最终答案: {answer[:200]}")
                break

            action_key = action.tool_name + "|" + json.dumps(
                action.args or {}, ensure_ascii=False, sort_keys=True
            )
            if action_key in executed:
                print("[ReAct] 检测到重复调用同一工具，直接采用上次观察作为答案")
                answer = executed[action_key]
                break

            # 执行工具，观察结果回填短期记忆，进入下一轮推理
            observation = self.exec_actions(action)
            executed[action_key] = observation
            print(f"[ReAct] 工具观察: {str(observation)[:200]}")
            short_term_memory.append(self.format_observations(response, action, observation))
        else:
            answer = (
                f"无法在 {max_steps} 步内完成任务，最后一步的观察结果："
                f"{short_term_memory[-1] if short_term_memory else '无'}"
            )
            print(f"[ReAct] 达到步数上限，强制结束")

        chat_history.add_user_message(task)
        chat_history.add_ai_message(answer)
        return answer

    def execute_stream(
        self,
        task: str,
        uuid: int,
        chat_history: ChatMessageHistory,
        verbose: bool = False,
        max_steps: int = 6,
    ):
        """
        流式执行（对标仓维云 chat_stream 事件流）：
        依次产出 tool_call / tool_result / content / complete 事件。
        用法: for event, payload in agent.execute_stream(...): ...
        """
        short_term_memory = []
        executed: dict[str, str] = {}
        for step in range(1, max_steps + 1):
            action, response = self.step_by_step(
                task=task,
                short_term_memory=short_term_memory,
                chat_history=chat_history,
                verbose=verbose,
            )
            if action is None:
                observation = "Error: 模型输出无法解析为合法动作 JSON，请严格按 ```json 格式重新输出动作。"
                short_term_memory.append(self.format_observations(response, None, observation))
                yield ("tool_error", {"step": step, "detail": observation})
                continue

            if action.tool_name == "Final Answer":
                args = action.args or {}
                answer = args.get("answer", "") or str(args)
                yield ("content", {"step": step, "answer": answer})
                break

            action_key = action.tool_name + "|" + json.dumps(
                action.args or {}, ensure_ascii=False, sort_keys=True
            )
            if action_key in executed:
                answer = executed[action_key]
                yield (
                    "content",
                    {"step": step, "answer": answer, "dedup": True},
                )
                break

            yield (
                "tool_call",
                {"step": step, "tool": action.tool_name, "args": action.args},
            )
            observation = self.exec_actions(action)
            executed[action_key] = observation
            yield (
                "tool_result",
                {"step": step, "tool": action.tool_name, "result": str(observation)[:500]},
            )
            short_term_memory.append(self.format_observations(response, action, observation))
        else:
            answer = f"无法在 {max_steps} 步内完成任务，请换个问法或补充信息。"
            yield (
                "content",
                {
                    "step": max_steps,
                    "answer": answer,
                },
            )

        chat_history.add_user_message(task)
        chat_history.add_ai_message(str(answer or "（无回答）"))
        yield ("complete", {"uuid": uuid})
