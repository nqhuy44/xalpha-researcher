---
trigger: always_on
---

Do Not Run Tests Automatically
This project uses AI services that consume tokens. Running tests during development can trigger unnecessary AI calls and significantly increase token usage.
Rule:
- Must never run tests automatically when generating or modifying code.
- Do not run npm test, pytest, go test, or any test command.
- Only run tests if the developer explicitly asks for it.
Always prioritize token efficiency and avoid any action that may cause repeated AI requests.