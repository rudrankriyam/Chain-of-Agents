from typing import Optional, Iterator, Dict
from .agents import WorkerAgent, ManagerAgent
from .utils import split_into_chunks, get_default_prompts
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChainOfAgents:
    """Main class for the Chain of Agents implementation."""
    
    def __init__(
        self,
        worker_model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",  # Together AI model
        manager_model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",  # Together AI model
        chunk_size: int = 500,
        worker_prompt: Optional[str] = None,
        manager_prompt: Optional[str] = None
    ):
        """
        Initialize the Chain of Agents.
        
        Args:
            worker_model: Model to use for worker agents
            manager_model: Model to use for manager agent
            chunk_size: Maximum tokens per chunk
            worker_prompt: Custom system prompt for workers
            manager_prompt: Custom system prompt for manager
        """
        default_worker_prompt, default_manager_prompt = get_default_prompts()
        
        self.worker_prompt = worker_prompt or default_worker_prompt
        self.manager_prompt = manager_prompt or default_manager_prompt
        self.chunk_size = chunk_size
        self.worker_model = worker_model
        self.manager_model = manager_model
        
        logger.info(f"Initialized Chain of Agents with {worker_model} workers and {manager_model} manager")
    
    def process(self, input_text: str, query: str) -> str:
        """
        Process a long text input using the Chain of Agents.
        
        Args:
            input_text: The long input text to process
            query: The user's query about the text
            
        Returns:
            str: The final response from the manager agent
        """
        # Split text into chunks
        chunks = split_into_chunks(input_text, self.chunk_size, self.worker_model)
        
        # Process chunks with worker agents
        worker_outputs = []
        previous_cu = None
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            worker = WorkerAgent(self.worker_model, self.worker_prompt)
            output = worker.process_chunk(chunk, query, previous_cu)
            worker_outputs.append(output)
            previous_cu = output
        
        # Synthesize results with manager agent
        manager = ManagerAgent(self.manager_model, self.manager_prompt)
        final_output = manager.synthesize(worker_outputs, query)
        
        return final_output 
    
    def process_stream(self, input_text: str, query: str, total_pages: int = 0) -> Iterator[Dict[str, str]]:
        """
        Process text with streaming - yields worker and manager messages.

        Args:
            input_text: The long input text to process
            query: The user's query about the text
            total_pages: Number of pages in the source document (0 if unknown)
        """
        worker_outputs = []
        previous_cu = None

        chunks = split_into_chunks(input_text, self.chunk_size, self.worker_model)
        total_chunks = len(chunks)

        # Debug logging for metadata
        metadata_message = {
            "type": "metadata",
            "content": json.dumps({
                "total_chunks": total_chunks,
                "total_pages": total_pages
            })
        }
        logger.info(f"Sending metadata: {metadata_message}")  # Debug log
        yield metadata_message
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{total_chunks}")
            worker = WorkerAgent(self.worker_model, self.worker_prompt)
            output = worker.process_chunk(chunk, query, previous_cu)
            worker_outputs.append(output)
            previous_cu = output
            
            # Debug logging for worker message
            worker_message = {
                "type": "worker",
                "content": output,
                "progress": {
                    "current": i + 1,
                    "total": total_chunks
                }
            }
            logger.info(f"Sending worker message: {worker_message}")  # Debug log
            yield worker_message
        
        logger.info("Processing manager synthesis")
        manager = ManagerAgent(self.manager_model, self.manager_prompt)
        final_output = manager.synthesize(worker_outputs, query)
        
        yield {
            "type": "manager",
            "content": final_output
        } 