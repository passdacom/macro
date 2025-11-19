# Gemini CLI Agent - Recommended Software Engineering Workflow

This document outlines the systematic approach for tackling software engineering tasks, emphasizing clarity, robustness, and adherence to project conventions. This workflow is designed to maximize efficiency, minimize errors, and ensure high-quality contributions.

## Core Principles

1.  **Understand First:** Never assume. Always gather comprehensive context before acting.
2.  **Plan Methodically:** Break down complex tasks. Prioritize. Anticipate potential issues.
3.  **Iterate & Verify:** Implement in small, testable steps. Verify continuously with tests, builds, and logs.
4.  **Communicate Clearly:** Provide concise, actionable information. Confirm understanding.
5.  **Respect Project Conventions:** Mimic existing style, structure, and patterns.

---

## Detailed Workflow Steps

### Step 1: Understand & Strategize

*   **Objective:** Gain a deep and comprehensive understanding of the user's request and the relevant codebase.
*   **Tools & Techniques:**
    *   `read_file`: For examining specific files (e.g., `README.md`, `개발_기록.md`, `추가_기능_개발_계획.md`, `requirements.txt`).
    *   `list_directory` / `glob`: To understand directory structures and locate relevant files.
    *   `search_file_content`: For targeted keyword or pattern searches within the codebase.
    *   `codebase_investigator`: **(For complex tasks like refactoring, bug root-cause analysis, or system-wide understanding)** This is the primary tool for building an architectural map, understanding dependencies, and gaining a holistic view.
*   **Deliverable:** A clear internal mental model of the task, its scope, and affected areas. For complex tasks, this may involve creating a preliminary analysis note.

### Step 2: Plan the Execution

*   **Objective:** Develop a coherent, step-by-step plan for implementing the task, prioritizing stability and testability.
*   **Tools & Techniques:**
    *   `write_todos`: Break down the task into smaller, manageable subtasks. Assign `pending` status.
    *   **Prioritization:** Identify critical path items and potential blockers.
    *   **Test Strategy:** Determine how to verify changes (unit tests, integration tests, manual checks).
*   **Deliverable:** A documented list of `TODO` items (using `write_todos`) and a high-level strategy communicated to the user if the task is complex.

### Step 3: Implement Iteratively

*   **Objective:** Apply changes to the codebase following the plan, ensuring each step is small and verifiable.
*   **Tools & Techniques:**
    *   `read_file`: Always read the target file immediately before making changes to ensure you're working with the latest content.
    *   `replace`: **(For small, targeted changes)** Requires exact `old_string` matching and ample context (3 lines before/after) to ensure precision. Use for surgical modifications.
    *   `write_file`: **(For creating new files or completely overwriting complex, refactored files)** Use for larger code blocks or when structural changes make `replace` too risky.
    *   `run_shell_command`: For executing build tools, linters, tests, or other system commands.
*   **Principles:**
    *   **Atomic Changes:** Aim for the smallest possible change that achieves a specific goal.
    *   **Contextual Awareness:** Adhere to existing code style, naming conventions, and architectural patterns.

### Step 4: Verify Continuously

*   **Objective:** Confirm that each change works as expected, meets requirements, and introduces no regressions. This is the *most critical* step.
*   **Tools & Techniques:**
    *   **Testing:**
        *   Identify existing test commands (e.g., `pytest`, `npm test`, `cargo test`).
        *   Write new unit or integration tests for new features or bug fixes.
        *   Execute relevant tests (`run_shell_command`).
    *   **Code Quality Checks:**
        *   Run project-specific linting (`npm run lint`, `ruff check .`).
        *   Execute type-checking (`tsc`, `mypy`).
        *   Perform build commands (`npm run build`, `cargo build`).
    *   **Log Analysis (CRUCIAL):**
        *   **Always clear previous logs** (`del macro_log.txt`) before a test run.
        *   Execute the application (`python main.py`).
        *   Perform the actions relevant to the changes.
        *   **Read and thoroughly analyze the *new* log file (`read_file macro_log.txt`)** to verify expected behavior, debug issues, and ensure no unexpected output or errors occur. This provides direct insight into runtime behavior.
    *   **Visual Confirmation:** For GUI applications, perform manual checks.
*   **Principles:**
    *   **Iterate on Feedback:** Use test and log results to refine the implementation.
    *   **Don't Assume:** Logs don't lie. Trust the output, not your intentions.

### Step 5: Finalize & Document

*   **Objective:** Ensure the work is complete, documented, and properly committed.
*   **Tools & Techniques:**
    *   `git status`: Confirm all intended changes are staged.
    *   `git diff --staged`: Review changes before committing.
    *   `git commit`: Write a clear, concise, and descriptive commit message focusing on *why* changes were made.
    *   `write_file` / `read_file`: Update relevant documentation files (e.g., `개발_기록.md`) with a summary of the work, challenges, and solutions.
    *   `run_shell_command` (`tar`): Create a project backup if requested or deemed necessary for major milestones.

---

## Lessons Learned from This Session

*   **The Log is King:** Logs provide the most direct insight into runtime behavior. Always prioritize clearing and analyzing fresh logs.
*   **No Silent Failures:** Expecting a `replace` or `write_file` to work perfectly without explicit verification can lead to chasing ghosts. Always re-read the file if there's any doubt.
*   **User Feedback is Paramount:** The user's direct observations are invaluable. Listen, re-evaluate, and methodically address each point.
*   **Architectural Soundness:** For complex problems, investing in a robust architecture (e.g., state machines) up-front, even if it takes time, prevents countless smaller bugs later.
*   **Separation of Concerns:** Keep components focused on their primary role (recorder records, grouper groups, player plays). Avoid mixing responsibilities to prevent subtle bugs.
*   **Patience and Persistence:** Complex bugs rarely yield to a single fix. A methodical, iterative approach is key.
*   **Explicit Rollback:** When a "perfect" state is identified, confirm it and be ready to revert if subsequent changes introduce regressions.
*   **Error Recovery:** Have a clear strategy for when tools (like `tar`) report partial failures.

By following these principles and steps, tasks can be executed efficiently and safely, leading to high-quality software solutions.
