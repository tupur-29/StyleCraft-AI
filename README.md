##🔄 StyleCraft AI

StyleCraft AI is a full-stack AI-powered web application designed to transform user queries into different response styles, such as casual and formal. It leverages a FastAPI backend for robust API services and a Streamlit frontend for an interactive user experience. AI-powered text generation is handled by a locally hosted Ollama instance serving the `qwen:0.5b` model.

## Features

*   **📝 User Query Input:** Allows users to input any text query.
*   **🔄 Style Selection:** Users can choose between "Casual" and "Formal" response styles.
*   **🤖 AI-Powered Transformation:** Utilizes the `qwen:0.5b` model via Ollama to regenerate the query in the selected style.
*   **📜 History Sidebar (Frontend):** Displays a history of queries and responses (if implemented as discussed).
*   **🚀 Robust Backend API:** Built with FastAPI, providing endpoints for text generation.
*   **🖥️ Interactive Frontend:** Clean and intuitive UI built with Streamlit.
*   **💾 Database Integration:** Stores queries and responses using PostgreSQL and SQLAlchemy.

## Technologies Used

**Backend:**
*   **Python 3.8+**
*   **FastAPI:** For building the RESTful API.
*   **Uvicorn:** ASGI server for FastAPI.
*   **Pydantic:** For data validation and settings management.
*   **SQLAlchemy:** ORM for database interaction.
*   **Psycopg2-binary:** PostgreSQL adapter for Python.
*   **Requests / HTTPX:** For making HTTP requests from the backend to the Ollama API.
*   **Python-dotenv:** For managing environment variables.
*   **Ollama:** For serving local LLMs (specifically `qwen:0.5b`).

**Frontend:**
*   **Streamlit:** For creating the web application UI.
*   **Requests:** For making HTTP requests from the frontend to the FastAPI backend.

**Database:**
*   **PostgreSQL:** Relational database for storing application data.

**Testing:**
*   **Pytest:** For running automated tests.
*   **HTTPX:** For asynchronous HTTP requests in tests (and potentially backend).
*   **Pytest-cov:** For test coverage reporting.

## Prerequisites

1.  **Python:** Version 3.8 or higher.
2.  **Pip & Virtualenv:** For managing Python packages and environments.
    ```bash
    python -m pip install --upgrade pip
    python -m pip install virtualenv
    ```
3.  **PostgreSQL Server:** A running instance of PostgreSQL. You'll need connection details (host, port, user, password, database name).
4.  **Ollama:**
    *   Install Ollama from [ollama.ai](https://ollama.ai/).
    *   Pull the `qwen:0.5b` model:
        ```bash
        ollama pull qwen:0.5b
        ```
    *   Ensure Ollama is running. By default, it serves an API at `http://localhost:11434`.

## Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone [your-repository-url]
    cd stylecraft-ai
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    python -m virtualenv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file with your specific configurations:
        ```env
        # Backend Configuration
        DATABASE_URL="postgresql://YOUR_DB_USER:YOUR_DB_PASSWORD@YOUR_DB_HOST:YOUR_DB_PORT/YOUR_DB_NAME"
        LOG_LEVEL="INFO"

        # Ollama Configuration (for FastAPI backend to connect to Ollama)
        OLLAMA_BASE_URL="http://localhost:11434" # Default Ollama API URL
        OLLAMA_MODEL_NAME="qwen:0.5b"           # Model to use
        OLLAMA_REQUEST_TIMEOUT=60               # Timeout in seconds for Ollama requests

        # Frontend Configuration (if Streamlit needs to know the backend URL explicitly)
        # Example: API_BASE_URL="http://localhost:8000/api/v1" # If served on different ports
        ```

5.  **Set up PostgreSQL Database:**
    *   Ensure your PostgreSQL server is running.
    *   Create the database specified in `DATABASE_URL` if it doesn't exist.
    *   Create the database user specified in `DATABASE_URL` with necessary permissions if they don't exist.
    *   Initialize the database schema. The application uses SQLAlchemy to define models. You might have a script or use Alembic for migrations. If not, ensure tables are created based on your SQLAlchemy models upon first run or via a specific setup script.
        *   *For a simple setup, the backend might create tables on startup if `Base.metadata.create_all(bind=engine)` is used, but for production, migrations (e.g., with Alembic) are recommended.*

## Running the Application

1.  **Ensure Ollama is Running:**
    *   Verify that Ollama is active and serving the `qwen:0.5b` model. You can test this by sending a request to `http://localhost:11434`.

2.  **Start the Backend (FastAPI):**
    *   Navigate to the backend application directory (e.g., `cd backend`).
    *   Run the Uvicorn server:
        ```bash
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ```
        (Replace `app.main:app` with your actual FastAPI app instance location if different.)
    *   The API will be available at `http://localhost:8000`.
    *   API documentation (Swagger UI) will be at `http://localhost:8000/docs`.

3.  **Start the Frontend (Streamlit):**
    *   Navigate to the frontend application directory (e.g., `cd frontend`).
    *   Run the Streamlit app:
        ```bash
        streamlit run app.py
        ```
    *   The frontend will typically be available at `http://localhost:8501`.

## Prompt Strategies for `qwen:0.5b` via Ollama

The effectiveness of StyleCraft AI heavily relies on the quality of prompts sent to the Ollama API. The `qwen:0.5b` model, being a smaller model, might require more explicit and clear instructions.

**General Approach:**

The backend will construct a prompt that includes:
1.  **System Message / Role Definition (Optional but Recommended):** Define the AI's role and overall goal.
2.  **Task Description:** Clearly state the task of rephrasing text into a specific style.
3.  **Style-Specific Instructions:** Provide keywords and guidance for the chosen style (Casual or Formal).
4.  **User's Query:** The original text input by the user.

## Running Tests

*   Navigate to the backend directory (or the root directory if tests are structured there).
*   Run Pytest:
    ```bash
    pytest
    ```
*   To include coverage reports:
    ```bash
    pytest --cov=app 
    ```
## License

MIT License
