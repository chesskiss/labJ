"""
Memory management for storing and retrieving conversation context.

This module provides functionality for storing past interactions,
experiments, and data for context-aware responses.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class Memory:
    """
    Memory manager for storing and retrieving conversation context.
    
    This class stores past interactions, experiments, and data to provide
    context-aware responses. Can be extended to use vector stores like
    FAISS or ChromaDB for semantic search.
    """
    
    def __init__(self, storage_path: Optional[Path] = None, use_vector_store: bool = False):
        """
        Initialize the memory manager.
        
        Args:
            storage_path: Path to store memory data
            use_vector_store: Whether to use vector store for semantic search
        """
        self.storage_path = storage_path or Path("data/logs/memory.json")
        self.use_vector_store = use_vector_store
        
        # In-memory storage
        self.interactions: List[Dict[str, Any]] = []
        self.experiments: List[Dict[str, Any]] = []
        self.data_points: List[Dict[str, Any]] = []
        
        # TODO: Initialize vector store if enabled
        # if use_vector_store:
        #     self.vector_store = self._initialize_vector_store()
        # else:
        #     self.vector_store = None
        
        # Load existing memory if storage path exists
        self._load_memory()
    
    def _initialize_vector_store(self):
        """
        Initialize vector store for semantic search.
        
        Returns:
            Vector store instance
        
        TODO: Implement vector store initialization (FAISS or ChromaDB)
        """
        # TODO: Implement vector store initialization
        # Option 1: FAISS
        # import faiss
        # dimension = 384  # For sentence transformers
        # index = faiss.IndexFlatL2(dimension)
        # return index
        #
        # Option 2: ChromaDB
        # import chromadb
        # client = chromadb.Client()
        # collection = client.create_collection("lab_assistant_memory")
        # return collection
        pass
    
    def _load_memory(self):
        """Load memory from storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.interactions = data.get("interactions", [])
                    self.experiments = data.get("experiments", [])
                    self.data_points = data.get("data_points", [])
                logger.info(f"Loaded memory from {self.storage_path}")
            except Exception as e:
                logger.error(f"Failed to load memory: {e}")
    
    def _save_memory(self):
        """Save memory to storage file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "interactions": self.interactions,
                "experiments": self.experiments,
                "data_points": self.data_points,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved memory to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    async def store_interaction(
        self,
        user_input: str,
        intent: Any,
        response: Any
    ):
        """
        Store an interaction in memory.
        
        Args:
            user_input: User's input text
            intent: Parsed intent
            response: Agent response
        """
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "intent_type": intent.type.value if hasattr(intent, 'type') else str(intent),
            "response": response.message if hasattr(response, 'message') else str(response),
            "metadata": {
                "intent": intent.__dict__ if hasattr(intent, '__dict__') else {},
                "response_data": response.__dict__ if hasattr(response, '__dict__') else {}
            }
        }
        
        self.interactions.append(interaction)
        
        # TODO: Store in vector store if enabled
        # if self.use_vector_store and self.vector_store:
        #     await self._add_to_vector_store(interaction)
        
        # Keep only last N interactions in memory (configurable)
        max_interactions = 1000
        if len(self.interactions) > max_interactions:
            self.interactions = self.interactions[-max_interactions:]
        
        self._save_memory()
    
    async def store_experiment(self, experiment_data: Dict[str, Any]):
        """
        Store experiment data.
        
        Args:
            experiment_data: Experiment data dictionary
        """
        experiment = {
            "timestamp": datetime.now().isoformat(),
            **experiment_data
        }
        
        self.experiments.append(experiment)
        self._save_memory()
    
    async def store_data_point(self, data_point: Dict[str, Any]):
        """
        Store a data point.
        
        Args:
            data_point: Data point dictionary
        """
        data_point_with_timestamp = {
            "timestamp": datetime.now().isoformat(),
            **data_point
        }
        
        self.data_points.append(data_point_with_timestamp)
        self._save_memory()
    
    async def retrieve_relevant(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant past interactions based on query.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
        
        Returns:
            List of relevant interactions
        
        TODO: Implement semantic search using vector store
        """
        # TODO: Implement semantic search
        # if self.use_vector_store and self.vector_store:
        #     return await self._semantic_search(query, limit)
        # else:
        #     return self._keyword_search(query, limit)
        
        # Simple keyword-based search for now
        return self._keyword_search(query, limit)
    
    def _keyword_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Simple keyword-based search.
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of matching interactions
        """
        query_lower = query.lower()
        relevant = []
        
        for interaction in self.interactions:
            user_input = interaction.get("user_input", "").lower()
            response = interaction.get("response", "").lower()
            
            # Simple keyword matching
            if any(word in user_input or word in response for word in query_lower.split()):
                relevant.append(interaction)
        
        return relevant[:limit]
    
    async def _semantic_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Semantic search using vector store.
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of relevant interactions
        
        TODO: Implement semantic search with embeddings
        """
        # TODO: Implement semantic search
        # 1. Generate embedding for query
        # 2. Search vector store for similar embeddings
        # 3. Return corresponding interactions
        pass
    
    def get_recent_interactions(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent interactions.
        
        Args:
            n: Number of interactions to return
        
        Returns:
            List of recent interactions
        """
        return self.interactions[-n:]
    
    def get_experiments(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all stored experiments.
        
        Args:
            limit: Maximum number of experiments to return
        
        Returns:
            List of experiments
        """
        if limit:
            return self.experiments[-limit:]
        return self.experiments
    
    def clear_memory(self):
        """Clear all stored memory."""
        self.interactions = []
        self.experiments = []
        self.data_points = []
        self._save_memory()
        logger.info("Cleared all memory")

