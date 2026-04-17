# Project Spec

The idea behind this project is to make a simple way to spin up RAG with an llm, and have a simple way to query the llm for information.

## AC

### Setup

Fill the docker compose volumes with the directories containing the information you want the llms to access

### On First Init

- [ ] Recursively find all files in the directories
- [ ] Add all paths to the sql db
- [ ] Generate vectors from all paths in the sql db
- [ ] Insert Vectors into ChromaDB

### On Querying

- [ ] LLM should use the RAG as a source
- [ ] LLM should always provide sources where the information came from
- [ ] LLM should admit if no information exists in the DB
- [ ] If the LLM is capable of accessing the internet, it should ask before getting information from external sources

### On RAG Directory changes

- [ ] Files should be monitored
- [ ] On adding a file immediately add it to the RAG
- [ ] On deleting a file, change the deleted flag in teh sql db from false to true
- [ ] Have a section in the FE that tracks deleted files, and allow the user to delete them from the vector db

## Stretch Goals

### Expand RAG with web sources

- [ ] Allow the LLM to store all information it has gotten from the internet and add it to the vector db
- [ ] Store all previous conversations for future reference by the LLM

## What will be required to achieve this?

- FE for querying the LLM
- BE to take in the query and make vector db queries to give the LLM, as well as parsing new files into the vector db, removing files from the db, etc. Will be written in python as that is standard for AI
- Model to be designated and hosted in docker
- ChromaDB for the vector storage
- ~~Sql db for keeping track of files in the vector db, and metadata on them~~ SQL may not be necessary for this, as vectors can sometimes have metadata that contains the original path source. There may be a way to keep a cache file instead of deleted paths.

### Technologies to be used

- TypeScript
- Vue.js
- Websocket
- Python
- Pip
- FastApi
- Tika (JRE & JDK required)
- Langchain
- Sentence-Transformers
- ChromaDb
- OpenAI
