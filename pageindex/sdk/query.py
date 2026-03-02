"""
PageIndex SDK Query Client

Async client for document retrieval and query operations.
Uses LLM-guided tree traversal for reasoning-based retrieval.
"""

import json
from typing import Optional, List

from .config import SDKConfig
from .models import QueryResult, SourceCitation, DocumentVersion, DocumentMetadata

import os
import importlib.util
import sys


def _get_persistence_module():
    """Load persistence module without triggering tiktoken import."""
    spec = importlib.util.spec_from_file_location(
        'persistence',
        os.path.join(os.path.dirname(__file__), '..', 'persistence.py')
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _get_utils_module():
    """Load utils module for OpenAI API calls."""
    # Mock tiktoken before loading utils
    if 'tiktoken' not in sys.modules:
        import types
        tiktoken_mock = types.ModuleType('tiktoken')
        tiktoken_mock.get_encoding = lambda x: None
        sys.modules['tiktoken'] = tiktoken_mock

    spec = importlib.util.spec_from_file_location(
        'utils',
        os.path.join(os.path.dirname(__file__), '..', 'utils.py')
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QueryClient:
    """Async client for query and retrieval operations."""

    def __init__(self, config: SDKConfig):
        """
        Initialize QueryClient.

        Args:
            config: SDK configuration
        """
        self._config = config
        self._repository = None
        self._utils = None

    def _get_repository(self):
        """Get repository instance (lazy initialization)."""
        if self._repository is None:
            persistence = _get_persistence_module()
            client = persistence.get_mongo_client(self._config.mongodb_uri)
            self._repository = persistence.PageIndexRepository(client, self._config.db_name)
        return self._repository

    def _get_utils(self):
        """Get utils module (lazy initialization)."""
        if self._utils is None:
            self._utils = _get_utils_module()
        return self._utils

    async def search(
        self,
        question: str,
        doc_id: str,
        version: Optional[int] = None,
    ) -> QueryResult:
        """
        Search for an answer in a document using reasoning-based tree traversal.

        Args:
            question: The question to answer
            doc_id: Document ID to search in
            version: Optional specific version (defaults to latest)

        Returns:
            QueryResult with answer and source citations

        Example:
            >>> result = await client.query.search("What is the revenue?", doc_id)
            >>> print(result.answer)
            >>> print(result.sources)
        """
        # Load document tree
        repository = self._get_repository()

        if version:
            doc_version = repository.get_version(doc_id, version)
        else:
            doc_version = repository.get_latest(doc_id)

        if doc_version is None:
            raise ValueError(f"Document not found: {doc_id}")

        tree = doc_version.tree

        # Traverse tree to find relevant nodes
        relevant_nodes = await self._traverse_tree(question, tree)

        # Extract context from relevant nodes
        context = self._extract_context(relevant_nodes, tree)

        # Generate answer using LLM
        answer = await self._generate_answer(question, context)

        # Build source citations
        sources = self._build_sources(relevant_nodes)

        return QueryResult(
            question=question,
            answer=answer,
            sources=sources,
            doc_id=doc_id,
        )

    async def _traverse_tree(self, question: str, tree: dict) -> List[str]:
        """
        Traverse the document tree using LLM guidance.

        Args:
            question: The question to answer
            tree: Document tree structure

        Returns:
            List of relevant node IDs
        """
        relevant_nodes = []
        nodes_to_check = []

        # Get root nodes
        if isinstance(tree, list):
            nodes_to_check = tree
        elif isinstance(tree, dict) and 'nodes' in tree:
            nodes_to_check = tree['nodes']
        else:
            nodes_to_check = [tree]

        # Breadth-first traversal with LLM guidance
        max_depth = 5
        current_depth = 0

        while nodes_to_check and current_depth < max_depth:
            current_depth += 1
            next_level = []

            # Process in batches to avoid too many API calls
            batch_size = min(len(nodes_to_check), 10)

            for i in range(0, len(nodes_to_check), batch_size):
                batch = nodes_to_check[i:i + batch_size]

                # Ask LLM which nodes are relevant
                relevant_in_batch = await self._select_relevant_nodes(question, batch)

                for node_id, is_relevant in relevant_in_batch:
                    node = self._find_node_by_id(nodes_to_check, node_id)
                    if node:
                        if is_relevant:
                            relevant_nodes.append(node_id)
                            # Add children for further exploration
                            if 'nodes' in node and node['nodes']:
                                next_level.extend(node['nodes'])
                        else:
                            # Still check children in case they're relevant
                            if 'nodes' in node and node['nodes']:
                                next_level.extend(node['nodes'])

            nodes_to_check = next_level

        return relevant_nodes

    async def _select_relevant_nodes(self, question: str, nodes: List[dict]) -> List[tuple]:
        """
        Use LLM to select which nodes are relevant to the question.

        Args:
            question: The question
            nodes: List of nodes to evaluate

        Returns:
            List of (node_id, is_relevant) tuples
        """
        if not nodes:
            return []

        utils = self._get_utils()

        # Build node summaries
        node_info = []
        for node in nodes:
            node_id = node.get('node_id', node.get('title', 'unknown'))
            title = node.get('title', 'Untitled')
            summary = node.get('summary', '')[:200] if node.get('summary') else ''
            node_info.append(f"- [{node_id}] {title}: {summary}")

        prompt = f"""Given this question: "{question}"

Which of these document sections are likely to contain the answer?

Sections:
{chr(10).join(node_info)}

Return a JSON array of objects with "node_id" and "relevant" (true/false).
Example: [{{"node_id": "0001", "relevant": true}}, {{"node_id": "0002", "relevant": false}}]

Only return the JSON array, nothing else."""

        try:
            response = utils.chatgpt_single(
                prompt,
                model=self._config.model,
                api_key=self._config.openai_api_key,
            )

            # Parse response
            result_text = response.strip()
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]

            selections = json.loads(result_text)
            return [(s.get('node_id'), s.get('relevant', False)) for s in selections]

        except Exception:
            # Fallback: mark all as potentially relevant
            return [(n.get('node_id', n.get('title')), True) for n in nodes]

    def _find_node_by_id(self, nodes: List[dict], node_id: str) -> Optional[dict]:
        """Find a node by its ID in a list."""
        for node in nodes:
            if node.get('node_id') == node_id or node.get('title') == node_id:
                return node
        return None

    def _extract_context(self, node_ids: List[str], tree: dict) -> str:
        """
        Extract text context from relevant nodes.

        Args:
            node_ids: List of relevant node IDs
            tree: Full document tree

        Returns:
            Combined context string
        """
        contexts = []

        def collect_text(node, collected):
            node_id = node.get('node_id', '')
            if node_id in node_ids:
                text_parts = []
                if node.get('title'):
                    text_parts.append(f"## {node['title']}")
                if node.get('summary'):
                    text_parts.append(f"Summary: {node['summary']}")
                if node.get('text'):
                    text_parts.append(f"Content: {node['text'][:1000]}")
                if text_parts:
                    collected.append('\n'.join(text_parts))

            for child in node.get('nodes', []):
                collect_text(child, collected)

        if isinstance(tree, list):
            for node in tree:
                collect_text(node, contexts)
        else:
            collect_text(tree, contexts)

        return '\n\n---\n\n'.join(contexts)

    async def _generate_answer(self, question: str, context: str) -> str:
        """
        Generate an answer using the LLM.

        Args:
            question: The question
            context: Relevant context from the document

        Returns:
            Generated answer
        """
        utils = self._get_utils()

        prompt = f"""Based on the following context from a document, answer the question.

Context:
{context}

Question: {question}

Provide a clear, concise answer based only on the context provided.
If the context doesn't contain enough information, say so."""

        response = utils.chatgpt_single(
            prompt,
            model=self._config.model,
            api_key=self._config.openai_api_key,
        )

        return response.strip()

    def _build_sources(self, node_ids: List[str]) -> List[SourceCitation]:
        """
        Build source citations from node IDs.

        Args:
            node_ids: List of relevant node IDs

        Returns:
            List of SourceCitation objects
        """
        sources = []

        def find_nodes(node, found):
            node_id = node.get('node_id', '')
            if node_id in node_ids:
                title = node.get('title', 'Untitled')
                start = node.get('start_index')
                end = node.get('end_index')

                page_range = None
                if start is not None and end is not None:
                    page_range = f"Pages {start}-{end}"

                text_snippet = None
                if node.get('text'):
                    text_snippet = node['text'][:200] + '...'
                elif node.get('summary'):
                    text_snippet = node['summary'][:200] + '...'

                found.append(SourceCitation(
                    node_id=node_id,
                    title=title,
                    page_range=page_range,
                    text_snippet=text_snippet,
                ))

            for child in node.get('nodes', []):
                find_nodes(child, found)

        # Note: We don't have access to the tree here, so we return basic sources
        for node_id in node_ids:
            sources.append(SourceCitation(
                node_id=node_id,
                title=f"Section {node_id}",
                page_range=None,
                text_snippet=None,
            ))

        return sources
