from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Action(BaseModel):
    tool_name: str = Field(description="The name of a tool")
    args: Optional[Dict[str, Any]] = Field(description="Input args of a tool, containing names and values")

    def __str__(self):
        rst = f"Action(tool_name={self.tool_name}"
        if self.args:
            for k, v in self.args.items():
                rst += f", {k}={v}"
        rst += ")"
        return rst
