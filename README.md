# cbsl-rag
RAG assistant over Central Bank of Sri Lanka reports
## Known issues
- Tables with text cells (e.g. lists of products) survive cleaning and end up inside chunks.
- Some special characters are garbled (e.g. "UKÆs" instead of "UK's").
- Some titles in metadata.csv contain line breaks.