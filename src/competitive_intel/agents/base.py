"""Base agent class with common functionality."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from competitive_intel.config import get_settings
from competitive_intel.models import AgentState, ConfidenceLevel, Entity, ResearchBrief
from competitive_intel.tools.search_tools import SearchToolset


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    name: str
    description: str
    system_prompt: str
    model: str | None = None
    temperature: float = 0.1
    max_tokens: int = 4096
    tools: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all agents in the competitive intelligence platform."""

    def __init__(
        self,
        config: AgentConfig,
        llm: BaseChatModel | None = None,
        search_tools: SearchToolset | None = None,
    ) -> None:
        self.config = config
        self.llm = llm or self._create_default_llm()
        self.search_tools = search_tools or SearchToolset()
        self._agent_id = uuid4()
        self._state: AgentState = AgentState()

    def _create_default_llm(self) -> BaseChatModel:
        """Create default LLM from settings."""
        settings = get_settings()
        return ChatOpenAI(
            model=settings.llm.model,
            temperature=settings.llm.temperature,
            max_tokens=settings.llm.max_tokens,
            api_key=settings.llm.api_key,
            timeout=settings.llm.timeout,
            max_retries=settings.llm.max_retries,
        )

    @property
    def agent_id(self) -> str:
        return str(self._agent_id)

    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    async def execute(self, state: AgentState, config: RunnableConfig | None = None) -> AgentState:
        """Execute the agent's main logic."""
        pass

    async def _call_llm(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        """Call the LLM with messages."""
        return await self.llm.ainvoke(messages, config=config, **kwargs)

    async def _stream_llm(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Any:
        """Stream LLM response."""
        return self.llm.astream(messages, config=config, **kwargs)

    def _build_messages(self, user_content: str, system_prompt: str | None = None) -> list[BaseMessage]:
        """Build message list with system and user messages."""
        messages: list[BaseMessage] = []

        if system_prompt or self.config.system_prompt:
            messages.append(SystemMessage(content=system_prompt or self.config.system_prompt))

        messages.append(HumanMessage(content=user_content))
        return messages

    def update_state(self, state: AgentState, **updates: Any) -> AgentState:
        """Update agent state with new values."""
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state

    def add_error(self, state: AgentState, error: str) -> AgentState:
        """Add an error to state."""
        state.errors.append(f"[{self.name}] {error}")
        return state

    def add_warning(self, state: AgentState, warning: str) -> AgentState:
        """Add a warning to state."""
        state.warnings.append(f"[{self.name}] {warning}")
        return state

    def set_step(self, state: AgentState, step: str) -> AgentState:
        """Set current step in state."""
        state.current_step = f"{self.name}.{step}"
        return state


class StructuredOutputAgent(BaseAgent):
    """Base agent that produces structured output using Pydantic models."""

    def __init__(
        self,
        config: AgentConfig,
        output_model: type[BaseModel],
        llm: BaseChatModel | None = None,
        search_tools: SearchToolset | None = None,
    ) -> None:
        super().__init__(config, llm, search_tools)
        self.output_model = output_model
        self._structured_llm = self.llm.with_structured_output(output_model)

    async def execute_structured(
        self,
        prompt: str,
        state: AgentState | None = None,
        config: RunnableConfig | None = None,
    ) -> BaseModel:
        """Execute and return structured output."""
        messages = self._build_messages(prompt)
        return await self._structured_llm.ainvoke(messages, config=config)


class AgentResult(BaseModel):
    """Standardized agent execution result."""

    agent_id: str
    agent_name: str
    success: bool
    output: Any = None
    state: AgentState | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)