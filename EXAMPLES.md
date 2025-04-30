# Examples

## Simple Task Processing

![Simple Task Processing](/assets/SimpleExample.png)

This is a minimal example showing a basic data flow:

1.  **Input:** A `DataInput` node provides an initial `Task1` object, like `{"actor": "niels"}`.
2.  **Processing:** A `TaskWorker` takes the `Task1`, modifies the `actor` field by prepending "processed this: ", and publishes a new `Task1`.
3.  **Output:** A `DataOutput` node receives and displays the final, processed `Task1` (e.g., `{"actor": "processed this: niels"}`).

This demonstrates the fundamental concept of passing data through a worker for transformation.

## Web Page Topic Extraction

![Web Page Topic Extraction](/assets/TopicExtractExample.png)

This example demonstrates a simple PlanAI workflow for extracting topics from a given web page URL.

**Workflow:**

1.  **Input:** The workflow starts with a `UrlInput` task containing the target URL (e.g., `https://www.provos.org/`).
2.  **Fetch Content:** A `TaskWorker` receives the `UrlInput`, uses `planai.integrations.WebBrowser` to fetch the page's content as Markdown, and publishes it as a `PageContent` task.
3.  **Extract Topics:** An `LLMTaskWorker` takes the `PageContent` and uses a configured LLM (like "O4 Mini") to analyze the text. Based on its prompt, it identifies and extracts key topics, structuring them into a `Topics` task. Each `Topic` within this list includes a `title`, `keywords` (as a list), and a `summary`.
4.  **Output:** A `DataOutput` node receives the final `Topics` task, presenting the extracted information.