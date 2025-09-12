# AI Agent for Scientific Research

This project provides a framework for building an AI agent for scientific research, complete with a backend server for managing scientific tools and a modern web UI for interaction and visualization.

## Project Structure

- `backend/`: The Python-based backend using FastAPI.
  - `app/`: The main application code.
    - `api/`: API endpoints, including the WebSocket for chat.
    - `agent/`: The AI agent's logic and tools.
    - `mcp/`: The server for managing scientific software.
  - `Dockerfile`: Dockerfile for the backend service.
  - `requirements.txt`: Python dependencies.

- `frontend/`: The React-based frontend.
  - `src/`: The main application code.
    - `components/`: React components for the UI.
    - `styles/`: CSS styles.
  - `Dockerfile`: Dockerfile for the frontend service.
  - `package.json`: Node.js dependencies.

- `docker-compose.yml`: Docker Compose file to run the entire application.

## How to Run

1. **Prerequisites:**
   - Docker
   - Docker Compose

2. **Build and Run:**

   ```bash
   docker-compose up --build
   ```

3. **Access the application:**

   - Open your browser and navigate to `http://localhost:8080`.

## How to Extend

- **Add AI Tools:**
  - Add new Python files with functions in the `backend/app/agent/tools/` directory.
  - The agent can be programmed to discover and use these tools.

- **Add Scientific Software Integrations:**
  - Add new methods to the `ToolController` class in `backend/app/mcp/tool_controller.py` to interface with your scientific software.

- **Customize the Frontend:**
  - Modify the React components in the `frontend/src/components/` directory to change the UI.
