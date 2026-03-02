import argparse
import os
import json
from datetime import datetime
from pageindex import *
from pageindex.page_index_md import md_to_tree


def get_page_count(toc_structure):
    """Extract page count from tree structure."""
    if not toc_structure:
        return 0

    def get_max_page(node):
        max_page = node.get('end_index', 0) or 0
        for child in node.get('nodes', []):
            max_page = max(max_page, get_max_page(child))
        return max_page

    if isinstance(toc_structure, list):
        return max(get_max_page(node) for node in toc_structure) if toc_structure else 0
    return get_max_page(toc_structure)


def estimate_token_count(toc_structure):
    """Estimate token count from tree structure (rough approximation)."""
    if not toc_structure:
        return 0

    def count_tokens(node):
        count = 0
        # Title tokens
        if node.get('title'):
            count += len(node['title'].split()) * 1.3
        # Summary tokens
        if node.get('summary'):
            count += len(node['summary'].split()) * 1.3
        # Text tokens
        if node.get('text'):
            count += len(node['text'].split()) * 1.3
        # Recurse into children
        for child in node.get('nodes', []):
            count += count_tokens(child)
        return int(count)

    if isinstance(toc_structure, list):
        return sum(count_tokens(node) for node in toc_structure)
    return count_tokens(toc_structure)


def save_to_mongodb(toc_structure, file_path, model, document_id, tags, doc_type, processing_version):
    """Save processed document to MongoDB."""
    from pageindex.persistence import PageIndexRepository, DocumentMetadata

    try:
        repo = PageIndexRepository()
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        print("Make sure MongoDB is running (try: docker-compose up -d)")
        return None

    # Create metadata
    metadata = DocumentMetadata(
        filename=os.path.basename(file_path),
        file_path=os.path.abspath(file_path),
        upload_date=datetime.utcnow(),
        page_count=get_page_count(toc_structure),
        token_count=estimate_token_count(toc_structure),
        model_used=model,
        processing_version=processing_version,
        tags=tags or [],
        doc_type=doc_type or ""
    )

    # Save to MongoDB
    version = repo.save(
        document_id=document_id,
        tree=toc_structure,
        metadata=metadata
    )

    return version


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process PDF or Markdown document and generate structure')
    parser.add_argument('--pdf_path', type=str, help='Path to the PDF file')
    parser.add_argument('--md_path', type=str, help='Path to the Markdown file')

    parser.add_argument('--model', type=str, default='gpt-4o-2024-11-20', help='Model to use')

    parser.add_argument('--toc-check-pages', type=int, default=20,
                      help='Number of pages to check for table of contents (PDF only)')
    parser.add_argument('--max-pages-per-node', type=int, default=10,
                      help='Maximum number of pages per node (PDF only)')
    parser.add_argument('--max-tokens-per-node', type=int, default=20000,
                      help='Maximum number of tokens per node (PDF only)')

    parser.add_argument('--if-add-node-id', type=str, default='yes',
                      help='Whether to add node id to the node')
    parser.add_argument('--if-add-node-summary', type=str, default='yes',
                      help='Whether to add summary to the node')
    parser.add_argument('--if-add-doc-description', type=str, default='no',
                      help='Whether to add doc description to the doc')
    parser.add_argument('--if-add-node-text', type=str, default='no',
                      help='Whether to add text to the node')

    # Markdown specific arguments
    parser.add_argument('--if-thinning', type=str, default='no',
                      help='Whether to apply tree thinning for markdown (markdown only)')
    parser.add_argument('--thinning-threshold', type=int, default=5000,
                      help='Minimum token threshold for thinning (markdown only)')
    parser.add_argument('--summary-token-threshold', type=int, default=200,
                      help='Token threshold for generating summaries (markdown only)')

    # MongoDB persistence arguments
    parser.add_argument('--persist', action='store_true', default=False,
                      help='Save processed document to MongoDB')
    parser.add_argument('--no-persist', dest='persist', action='store_false',
                      help='Do not save to MongoDB (default behavior)')
    parser.add_argument('--document-id', type=str, default=None,
                      help='Existing document ID for versioning (generates new ID if not provided)')
    parser.add_argument('--tags', type=str, default=None,
                      help='Comma-separated tags for the document')
    parser.add_argument('--doc-type', type=str, default=None,
                      help='Document category (e.g., financial, legal, academic)')

    args = parser.parse_args()

    # Validate that exactly one file type is specified
    if not args.pdf_path and not args.md_path:
        raise ValueError("Either --pdf_path or --md_path must be specified")
    if args.pdf_path and args.md_path:
        raise ValueError("Only one of --pdf_path or --md_path can be specified")

    # Parse tags
    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(',') if t.strip()]

    # Processing version (using model + timestamp as version identifier)
    processing_version = f"pageindex-{args.model}"

    file_path = args.pdf_path or args.md_path

    if args.pdf_path:
        # Validate PDF file
        if not args.pdf_path.lower().endswith('.pdf'):
            raise ValueError("PDF file must have .pdf extension")
        if not os.path.isfile(args.pdf_path):
            raise ValueError(f"PDF file not found: {args.pdf_path}")

        # Process PDF file
        # Configure options
        opt = config(
            model=args.model,
            toc_check_page_num=args.toc_check_pages,
            max_page_num_each_node=args.max_pages_per_node,
            max_token_num_each_node=args.max_tokens_per_node,
            if_add_node_id=args.if_add_node_id,
            if_add_node_summary=args.if_add_node_summary,
            if_add_doc_description=args.if_add_doc_description,
            if_add_node_text=args.if_add_node_text
        )

        # Process the PDF
        toc_with_page_number = page_index_main(args.pdf_path, opt)
        print('Parsing done...')

    elif args.md_path:
        # Validate Markdown file
        if not args.md_path.lower().endswith(('.md', '.markdown')):
            raise ValueError("Markdown file must have .md or .markdown extension")
        if not os.path.isfile(args.md_path):
            raise ValueError(f"Markdown file not found: {args.md_path}")

        # Process markdown file
        print('Processing markdown file...')

        # Process the markdown
        import asyncio

        # Use ConfigLoader to get consistent defaults (matching PDF behavior)
        from pageindex.utils import ConfigLoader
        config_loader = ConfigLoader()

        # Create options dict with user args
        user_opt = {
            'model': args.model,
            'if_add_node_summary': args.if_add_node_summary,
            'if_add_doc_description': args.if_add_doc_description,
            'if_add_node_text': args.if_add_node_text,
            'if_add_node_id': args.if_add_node_id
        }

        # Load config with defaults from config.yaml
        opt = config_loader.load(user_opt)

        toc_with_page_number = asyncio.run(md_to_tree(
            md_path=args.md_path,
            if_thinning=args.if_thinning.lower() == 'yes',
            min_token_threshold=args.thinning_threshold,
            if_add_node_summary=opt.if_add_node_summary,
            summary_token_threshold=args.summary_token_threshold,
            model=opt.model,
            if_add_doc_description=opt.if_add_doc_description,
            if_add_node_text=opt.if_add_node_text,
            if_add_node_id=opt.if_add_node_id
        ))

        print('Parsing done...')

    # Always save to file (existing behavior preserved)
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = './results'
    output_file = f'{output_dir}/{file_name}_structure.json'
    os.makedirs(output_dir, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(toc_with_page_number, f, indent=2, ensure_ascii=False)

    print(f'Tree structure saved to: {output_file}')

    # Optionally persist to MongoDB
    if args.persist:
        print('Saving to MongoDB...')
        version = save_to_mongodb(
            toc_structure=toc_with_page_number,
            file_path=file_path,
            model=args.model,
            document_id=args.document_id,
            tags=tags,
            doc_type=args.doc_type,
            processing_version=processing_version
        )

        if version:
            print(f'Document saved to MongoDB:')
            print(f'  Document ID: {version.document_id}')
            print(f'  Version: {version.version}')
            print(f'  Created at: {version.created_at.isoformat()}')
        else:
            print('Warning: Failed to save to MongoDB')
