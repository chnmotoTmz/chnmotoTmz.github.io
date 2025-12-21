# Hatena Blog Suite

A comprehensive automated blog post generation and management system for Hatena Blog. This system integrates LLMs (Gemini, Claude) to generate high-quality, narrative-driven content, fetch web and video summaries, and publish directly to Hatena Blog.

## Features

- **Automated Content Generation**: Uses Gemini and Claude to write articles based on user inputs or topics.
- **Workflow Engine**: Flexible, JSON-defined workflows for orchestrating tasks.
- **Multi-Blog Support**: Manage multiple blogs from a single instance.
- **RAG & Web Integration**: Fetches relevant web content and uses internal RAG (Retrieval-Augmented Generation) for context.
- **Thumbnail Generation**: Automatically generates and uploads thumbnails using custom APIs or Magic Hour.
- **LINE Integration**: Trigger workflows and receive notifications via LINE.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd hatena-blog-suite
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration**:
    -   Ensure `blogs.yml` is configured with your Hatena Blog credentials and LINE channel IDs.
    -   Set up your `.env` file (or `.env.develop`) with necessary API keys (Gemini, LINE, etc.).

## Usage

The application can be run in two modes: **Server Mode** (default) or **CLI Mode** (for specific workflows).

### 1. Server Mode

Starts the Flask web server to handle webhooks (e.g., from LINE) and API requests.

```bash
python run_app.py
```

-   **Access**: `http://localhost:8000`
-   **Logs**:
    -   Debug logs: `logs/debug_YYYYMMDD_HHMMSS.log`
    -   Prompt logs: `logs/prompts_YYYYMMDD_HHMMSS.log`

### 2. CLI Mode (New!)

Execute specific workflows directly from the command line without starting the web server. This is useful for testing, debugging, or running manual tasks.

#### Syntax

```bash
python run_app.py --flow <workflow_name_or_path> [--topic <your_topic>]
```

-   `--flow`: The name of the workflow file (without extension) or full path to the JSON file.
-   `--topic`: (Optional) The primary topic or text input for the article generation. Defaults to "Python programming tips".

#### Example: Simple Hatena Flow

Run a minimal workflow that generates a text article, adds a thumbnail, and publishes it to Hatena Blog.

```bash
python run_app.py --flow simple_hatena_flow --topic "最近のAI技術の進化について"
```

This workflow (`src/workflows/simple_hatena_flow.json`) performs the following steps:
1.  **Generate Content**: Writes a short article based on the provided topic.
2.  **Generate Thumbnail**: Creates a thumbnail image based on the article content.
3.  **Persist Draft**: Saves the article to the local database.
4.  **Publish**: Posts the article to the configured Hatena Blog.

## Directory Structure

-   `src/`: Source code.
    -   `apps/`: Application-specific workflow definitions.
    -   `services/`: Core logic and service integrations (Gemini, Hatena, etc.).
    -   `tasks/`: Reusable task modules for workflows.
    -   `workflows/`: Shared workflow definitions (JSON).
-   `logs/`: Application logs.
-   `tests/`: Unit and integration tests.

## Troubleshooting

-   **Missing Thumbnails**:
    -   Check `logs/debug_*.log` for "ThumbnailGenerator" entries.
    -   Ensure `CUSTOM_THUMBNAIL_API_URL` is reachable if using a local image generator.
    -   Verify `ALLOW_MAGICHOUR_FALLBACK` in `.env` if you want to allow fallback to external APIs.

## License

[License Information]
