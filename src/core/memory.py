from typing import List, Optional
from loguru import logger
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.types import Experience, MemoryEntry

class HierarchicalMemory:
    def __init__(self, meta_model: Optional[BaseChatModel] = None):
        self.working_memory: List[Experience] = []
        self.episodic_memory: List[Experience] = []
        self.procedural_memory: List[MemoryEntry] = []
        self.episodic_threshold = 0.7
        self.meta_model = meta_model

    async def write(self, experience: Experience):
        self.working_memory.append(experience)
        if experience.importance > self.episodic_threshold:
            self.episodic_memory.append(experience)
        
        # Periodically trigger abstraction
        if len(self.episodic_memory) >= 5:
            await self._abstract_procedural_memory()

    async def retrieve(self, query: str, k: int = 5) -> List[Experience]:
        working = self.working_memory[-3:]
        episodic = [e for e in self.episodic_memory if query.lower() in e.task.lower()][:k]
        return working + episodic

    async def _abstract_procedural_memory(self):
        """Uses the meta-model to extract general rules from episodic memories."""
        if not self.meta_model:
            logger.warning("No meta-model provided for memory abstraction.")
            return

        logger.info("Abstracting episodic memory into procedural rules...")
        
        recent_episodes = [f"Task: {e.task}\nOutcome: {e.outcome}\nLessons: {e.lessons}" for e in self.episodic_memory[-5:]]
        episodes_str = "\n---\n".join(recent_episodes)

        system_msg = SystemMessage(content=(
            "You are a Knowledge Abstraction Engine. Your goal is to analyze a set of episodic memories "
            "from financial analysis tasks and extract 1-2 'Procedural Rules' (general heuristics or best practices). "
            "These rules should be high-level and applicable to future tasks. "
            "Output ONLY the rules, one per line."
        ))
        
        response = await self.meta_model.ainvoke([system_msg, HumanMessage(content=episodes_str)])
        
        new_rules = response.content.strip().split("\n")
        for rule in new_rules:
            if rule.strip():
                self.procedural_memory.append(MemoryEntry(
                    id=f"rule_{len(self.procedural_memory)}",
                    content=rule.strip(),
                    importance=0.9,
                    tags=["abstracted", "procedural"]
                ))

    def get_procedural_rules(self) -> List[MemoryEntry]:
        return self.procedural_memory
