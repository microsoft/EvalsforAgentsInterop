# Evals for Agent Interop Webapp

A modern web application for evaluating and comparing AI agents across custom datasets, test cases, and rubrics. The app provides a workflow for dataset creation, evaluation runs, detailed results, and leaderboard analytics.

## Features & Pages

### 1. Datasets Page
- **Purpose:** View and manage all evaluation datasets.
- **Features:**
  - List all datasets with metadata (name, test case count, last updated)
  - Create new datasets
  - Click a dataset to view details

### 2. Dataset Detail Page
- **Purpose:** Review a dataset's structure and test cases.
- **Features:**
  - See dataset description, creation, and update dates
  - List all test cases with prompts, reference documents, and evaluation criteria
  - Edit or delete the dataset

### 3. Create/Edit Dataset Pages
- **Purpose:** Add or modify datasets and their test cases.
- **Features:**
  - Enter dataset name and description
  - Select evaluation criteria (e.g., correctness, groundedness, tool efficiency)
  - Add, edit, or remove test cases (with prompts, reference docs, criteria)

### 4. Results Page
- **Purpose:** View all completed and ongoing evaluation runs.
- **Features:**
  - List evaluation runs with summary metrics (date, datasets, agents, scores)
  - Click a run to see detailed results

### 5. Run Evaluation Page
- **Purpose:** Configure and start a new evaluation run.
- **Features:**
  - Name the evaluation
  - Select datasets and specific test cases
  - Select agents to evaluate
  - Start the run and view progress

### 6. Evaluation Detail Page
- **Purpose:** Drill down into a single evaluation run.
- **Features:**
  - Show overall and per-metric scores (groundedness, tool efficiency, accuracy, relevance)
  - List results by agent and dataset
  - Expand to see individual test case results, scores, and feedback

### 7. Leaderboard Page
- **Purpose:** Compare agent performance across all evaluations.
- **Features:**
  - Tabbed interface for different rubrics (overall, groundedness, tool efficiency, accuracy, relevance)
  - Podium and ranking for top agents
  - See evaluation counts and scores per agent

## How to Run the Webapp

> **Note:** The webapp is a React-based frontend built with Vite and TypeScript.

### With Docker (Recommended)

```bash
# From repo root
docker-compose up

# Webapp will be available at http://localhost:5000
```

### Locally

> **Prerequisites:** Node.js 18+ and npm installed

1. **Install dependencies**
   ```bash
   cd src/webapp
   npm install
   ```

2. **Configure Environment Variables** (optional)
   
   The webapp uses environment variables for configuration. Copy the example file and customize as needed:
   
   ```bash
   cp .env.example .env
   ```
   
   Key environment variables:
   - `VITE_API_URL`: API endpoint (default: `http://localhost:8000/api`)
   - `VITE_ENABLE_RUBRICS_UX`: Show/hide rubrics in UI (default: `false`)
   
   Or set them directly:
   
   ```bash
   export VITE_API_URL=http://your-api-url/api
   export VITE_ENABLE_RUBRICS_UX=false
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

4. **Access the webapp**
   
   Open http://localhost:5173 in your browser (Vite dev server uses port 5173 by default)

### Build for Production

```bash
cd src/webapp
npm run build
# Output will be in the dist/ directory
```

## Configuration & Feature Flags

The webapp supports the following configuration options via environment variables:

### API Configuration
- **`VITE_API_URL`**: Backend API endpoint
  - Default: `http://localhost:8000/api`
  - Example: `VITE_API_URL=https://api.example.com/api`

### Feature Flags

#### Rubrics UX (`VITE_ENABLE_RUBRICS_UX`)
Controls visibility of evaluation rubrics throughout the user interface.

- **Default**: `false` (rubrics hidden)
- **When enabled**: Rubrics are displayed in:
  - Test case detail pages (rubric cards with Azure Foundry ID, threshold, and payload)
  - Evaluation result pages (rubric summary information)
  - Tool expectation cards (rubric details within tool arguments)
- **When disabled**: All rubric-related UI elements are hidden
- **Note**: This is purely a UX control and does not affect evaluator behavior

**Usage**:
```bash
# Enable rubrics UX
VITE_ENABLE_RUBRICS_UX=true

# Disable rubrics UX (default)
VITE_ENABLE_RUBRICS_UX=false
```

## Project Structure
- `src/components/` � React components for each page and UI element
- `src/hooks/useSeedData.ts` � Seeds demo data on first load
- `PRD.md` � Product requirements and design notes
- `SECURITY.md` � Security policy

## License
See [LICENSE](./LICENSE).
