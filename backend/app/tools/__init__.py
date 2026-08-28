"""LangGraph 问答 Agent 的工具集"""

from app.tools.jd_match import match_job
from app.tools.knowledge import query_knowledge
from app.tools.notes import gen_study_notes
from app.tools.project import dig_project, project_intro

ALL_TOOLS = [query_knowledge, match_job, gen_study_notes, dig_project, project_intro]
