from .main import ChainOfAgents
from .agents import WorkerAgent, ManagerAgent
from .utils import split_into_chunks, count_words

__version__ = "0.1.0"

__all__ = [
    "ChainOfAgents",
    "WorkerAgent",
    "ManagerAgent",
    "split_into_chunks",
    "count_words"
] 