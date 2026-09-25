# CropTrac AI Assistant

CropTrac is an AI assistant that helps farm users find information by asking questions in everyday language.

Instead of searching through farm records manually, a user can ask questions such as:

- How many harvests are still pending?
- Which crops are connected to each field?
- What is the total harvested area for each crop?

> **Current status:** CropTrac is an early prototype. It is not ready for production use until the database security rules and system setup are completed.

## What It Can Do

- Lets users sign in before asking questions
- Answers questions using the user's own database records
- Remembers previous questions for the same user
- Turns questions into database searches
- Checks database searches before running them
- Prevents the AI from changing or deleting data
- Keeps conversations available when the user returns

## Technology Stack

| Technology | What it is used for |
| --- | --- |
| **Python** | Runs the CropTrac application. |
| **Groq** | Provides the AI model used to understand questions and write answers. The project uses `openai/gpt-oss-120b`. |
| **LangGraph** | Manages the conversation and remembers each user's previous messages. |
| **PostgreSQL** | Stores farm data and the user's conversation history. |
| **SQLGlot** | Checks AI-generated database searches for unsafe or unwanted actions. |
| **Hugging Face** | Provides the `all-MiniLM-L6-v2` model used to turn text into searchable vectors. |
| **PGVector** | Stores these vectors in PostgreSQL for future document search. This feature is prepared but not yet connected to the assistant. |
| **Requests and PyJWT** | Handle login and read the user's ID from the login token. |
| **uv** | Installs and manages the project's Python packages. |

## How It Works

1. The user signs in through CropTrac's login service.
2. The assistant reads the user's ID from the login token.
3. The user asks a question in normal language.
4. The AI creates a database search to find the answer.
5. CropTrac checks that the search is safe and allowed.
6. PostgreSQL returns the user's permitted records.
7. The AI turns those records into an easy-to-read answer.

The assistant is designed to read data, not change it.

## Before You Start

You will need:

- Python 3.12 or a newer version
- [uv](https://docs.astral.sh/uv/)
- Access to a PostgreSQL database
- A Groq API key
- A CropTrac login service
- A database administrator to configure user access rules

Your database administrator must ensure that each user can only access their own farm records. CropTrac sets the current user's ID before every database search, but the database itself must use that ID to restrict the records shown.

## Installation

Open a terminal in the project folder and install the packages:

```bash
uv sync
```

Create your local settings file.

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

## Settings

Open `.env` and add the following values:

```dotenv
GROQ_API_KEY=your_groq_api_key
DATABASE_URL_DEV=postgresql://username:password@localhost:5432/database_name
AUTH_SERVER_URL=https://login.example.com
```

| Setting | Where to get it |
| --- | --- |
| `GROQ_API_KEY` | Create an account with Groq and generate an API key. |
| `DATABASE_URL_DEV` | Ask the database administrator for the development database connection details. |
| `AUTH_SERVER_URL` | Ask the application team for the CropTrac login service address. |

CropTrac will stop with an error if any of these settings is missing.

## Start the Assistant

Run:

```bash
uv run python run_agent.py
```

You will be asked for your login details. After signing in, type your question and press Enter.

Type `quit`, `exit`, or `q` to close the assistant.

The package shortcut is not ready because of a naming mistake in `pyproject.toml`, so use the command above.

## Data Safety

CropTrac adds several safety checks before running an AI-generated database search:

- Only reading operations are allowed
- Changes, deletions, and table updates are blocked
- Only approved farm tables can be read
- Important user and password tables are blocked
- Database access is limited to the signed-in user when RLS is configured correctly

These checks are helpful, but they do not replace normal database security. Before using real farm data, the system should also use:

- A restricted database login
- Row-Level Security for every user's records
- Column permissions for sensitive information
- Query time and result limits
- Strong login credentials without development defaults

## Current Limitations

- The AI is not yet given a complete description of the database, so it may write incorrect searches.
- The list of approved database tables is currently fixed in the code.
- The document-upload and search process has not been built yet.
- Database user-access rules must be prepared separately.
- There are no limits yet for how long or how large a database search can be.
- Development login details are included in `run_agent.py` and must be removed before release.
- The application has not yet been fully tested and approved for production.

## Common Problems

### CropTrac says a setting is missing

Make sure the file is named `.env`, is in the project folder, and contains all three settings.

### Login fails

Check the login service address and make sure the account is active. The login service must provide an access token containing the user's ID.

### The database reports an extension or permission error

Ask the database administrator to confirm that PostgreSQL has the `vector` extension and that the application can create and use the required tables.

### The AI cannot answer correctly

The assistant may not understand the database structure yet. The approved table list, field names, and AI instructions may need to be updated.

### A user can see too many records

Stop using the system with real data and ask the database administrator to check Row-Level Security. Also make sure the database login does not have permission to bypass these rules.
