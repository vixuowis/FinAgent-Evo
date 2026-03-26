from typing import List, Optional
from src.core.types import Experience, MemoryEntry

class HierarchicalMemory:
    def __init__(self):
        self.working_memory: List[Experience] = []
        self.episodic_memory: List[Experience] = []
        self.procedural_memory: List[MemoryEntry] = []
        self.episodic_threshold = 0.7

    async def write(self, experience: Experience):
        self.working_memory.append(experience)
        if experience.importance > self.episodic_threshold:
            self.episodic_memory.append(experience)
        
        if len(self.episodic_memory) > 10:
            self._abstract_procedural_memory()

    async def retrieve(self, query: str, k: int = 5) -> List[Experience]:
        working = self.working_memory[-3:]
        episodic = [e for e in self.episodic_memory if query.lower() in e.task.lower()][:k]
        return working + episodic

    def _abstract_procedural_memory(self):
        print("Abstracting episodic memory into procedural memory...")

    def get_procedural_rules(self) -> List[MemoryEntry]:
        return self.procedural_memory
