---
name: add-connection
description: Add and test a new database connection profile and save it to connections.json.
---

# /agentic-discovery:add-connection

Adds a new database connection profile with automated connection verification.

### Syntax
```bash
/agentic-discovery:add-connection [name] [db_url] [schema] [description]
```

### Examples
```bash
python run.py --add-conn my_postgres "postgresql://user:pass@localhost:5432/mydb" public "Production Postgres"
```
