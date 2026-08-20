from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ToolResult[T: BaseModel](BaseModel, Generic[T]):
    data: T
