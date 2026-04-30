# Project Spec

The idea behind this project is to make a simple way to spin up RAG with an llm, and have a simple way to query the llm for information.

## AC

### Setup

Fill the `./data/` directory with the files you want the LLM to access. They are mounted into the BE container at `/data` and ingested automatically on startup.

### On First Init

- [x] Recursively find all files in the directories
- [x] Add all paths to the vector db (ChromaDB metadata tracks source paths)
- [x] Generate vectors from all files using sentence-transformers
- [x] Insert Vectors into ChromaDB

### On Querying

- [x] LLM should use the RAG as a source
- [x] LLM should always provide sources where the information came from
- [x] LLM should admit if no information exists in the DB
- [ ] If the LLM is capable of accessing the internet, it should ask before getting information from external sources

### On RAG Directory changes

- [x] Files should be monitored
- [x] On adding a file immediately add it to the RAG
- [x] On deleting a file, change the deleted flag in the vector db metadata from false to true
- [x] Have a section in the FE that tracks deleted files, and allow the user to delete them from the vector db

## Stretch Goals

### Expand RAG with web sources

- [ ] Allow the LLM to store all information it has gotten from the internet and add it to the vector db
- [ ] Store all previous conversations for future reference by the LLM

## What will be required to achieve this?

- FE for querying the LLM
- BE to take in the query and make vector db queries to give the LLM, as well as parsing new files into the vector db, removing files from the db, etc. Will be written in python as that is standard for AI
- Model to be designated and hosted in docker (Ollama with qwen3:1.7b, auto-pulled on first start)
- ChromaDB for the vector storage
- File metadata (source paths, deleted flag) tracked in ChromaDB document metadata — no separate SQL DB needed

### Technologies used

- TypeScript
- Vue.js
- Websocket
- Python
- Pip
- FastAPI
- Apache Tika (running as a Docker service — no local JRE needed)
- LangChain
- Sentence-Transformers
- ChromaDB
- Ollama (local LLM inference via native API)
- Docker Compose
- Redis
