# APP Specific

For this classical-japanese-assistant app, we are using python3 in a venv virtual environment. We start the process with start.sh

# General Coding Style & Philosophy

- Everything we create should be modular and created in a way that can be both scalable and portable. Avoid hard coding variables, features, model names etc whereever possible.
- Favor readability and simplicity over cleverness.
- Write code as if someone else will read it tomorrow.
- Prioritize maintainability and clear commenting.
- Embrace idiomatic, modern language features but don’t overcomplicate.
- Include brief comments explaining intent where unclear.
- Prefer explicitness over implicit magic.
- Test your code well; automated tests preferred.

# Workflow & Collaboration

- Commit small, focused changes with descriptive messages.
- Use feature branches for new functionality.
- Prioritize code review feedback and iterate quickly.
- Be respectful, constructive, and positive in comments and PRs.
- Document assumptions and decisions clearly inline or in docs.
- Run tests locally before pushing.
- Avoid merge conflicts by regularly syncing with main branch.

# Best Practices & Tools

- Use consistent formatting and linting tools (e.g., Prettier, ESLint).
- Keep dependencies up to date but audit for vulnerabilities.
- Write modular, reusable components/functions.
- Keep functions small and focused on single responsibilities.
- Handle errors gracefully with clear messages.
- Optimize performance only after correctness and clarity.

# Environment & Context

- Assume Node.js 18+ environment for this codebase.
- Use ES modules and latest stable language features.
- Don't use deprecated libraries or unsafe patterns.
- Prefer promises/async-await for async work over callbacks.

# Testing & Debugging

- Write unit tests for critical and complex logic.
- Use descriptive test names reflecting behavior and edge cases.
- Debug proactively—log, step through, and analyze failures.
- Refactor test code as thoughtfully as production code.

# Communication Tone

- Be clear, concise, and polite.
- Avoid jargon unless necessary, clarify when used.
- Encourage curiosity and open to learning new approaches.