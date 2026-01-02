# GitHub Copilot Custom Agents

This directory contains custom GitHub Copilot agents that extend Copilot's capabilities with specialized expertise.

## What are Custom Agents?

Custom agents are specialized AI assistants that you can create to handle specific types of development tasks. Each agent has:

- **A unique name**: Used to invoke the agent (e.g., `@code-reviewer`)
- **Specific expertise**: Detailed knowledge in a particular domain
- **Custom instructions**: Guidelines that shape the agent's behavior and responses

## How to Use These Agents

1. **In GitHub Copilot Chat**: Type `@agent-name` followed by your request
2. **In Pull Requests**: Mention the agent in a comment
3. **In Issues**: Reference the agent for specialized assistance

Example:

```
@code-reviewer Please review this function for potential security issues
```

## Available Agents

| Agent                    | Purpose                  | Best For                                        |
| ------------------------ | ------------------------ | ----------------------------------------------- |
| `@code-reviewer`         | Code quality reviews     | Pull request reviews, code improvements         |
| `@documentation-writer`  | Technical documentation  | README files, API docs, comments                |
| `@test-generator`        | Test case generation     | Unit tests, integration tests, coverage         |
| `@security-analyzer`     | Security analysis        | Vulnerability detection, secure coding          |
| `@refactoring-expert`    | Code refactoring         | Code smells, design patterns, cleanup           |
| `@bug-hunter`            | Bug detection & fixing   | Debugging, error analysis, issue resolution     |
| `@performance-optimizer` | Performance optimization | Bottlenecks, algorithm improvements, efficiency |

## Agent Files Structure

Each agent is a single markdown file:

```
agent-name.agent.md    # Agent configuration and instructions
```

**File format:**

```markdown
---
name: agent-name
description: Brief summary of capabilities
tools: ['read', 'search', 'edit']
---

Detailed behavior guidelines in plain text/markdown format
```

**Components:**

1. **YAML frontmatter** (between `---` markers):

   - `name` (required): The agent's identifier
   - `description` (required): Brief summary of capabilities
   - `tools` (optional): Available tools for the agent

2. **Content** (after frontmatter):
   - Plain text/markdown with detailed behavior guidelines

## Creating Your Own Agent

1. Create a new file in the `.github/agents/` directory named `your-agent-name.agent.md`
2. Add YAML frontmatter with your configuration (`name`, `description`, and optionally `tools`)
3. After the frontmatter, write clear, specific guidelines in plain text/markdown
4. Test the agent with various scenarios
5. Iterate based on results

## Tips for Effective Agent Use

- **Be specific**: Clearly state what you want the agent to do
- **Provide context**: Share relevant code, error messages, or requirements
- **Use the right agent**: Choose the agent that matches your task
- **Iterate**: Refine your requests based on agent responses
- **Combine agents**: Use multiple agents for complex tasks

## Maintenance

- Keep instructions up-to-date with best practices
- Refine agent behavior based on usage patterns
- Add new agents as needed for specialized tasks
- Remove or merge redundant agents

## Learn More

- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
- [Custom Agents Guide](https://docs.github.com/en/copilot/customizing-copilot/creating-custom-agents)
