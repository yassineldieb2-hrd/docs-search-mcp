# RAG basics

## Chunking
Split documents into chunks of roughly 100-200 words with a small overlap so an answer is rarely cut in half.

## Hybrid search
Combine vector similarity with keyword search and merge the rankings with Reciprocal Rank Fusion.

## Evaluation
Measure retrieval separately from generation using hit rate at k and mean reciprocal rank.
