export const CATEGORIES = [
  { value: 'dev',      label: 'Development' },
  { value: 'qa',       label: 'QA / Testing' },
  { value: 'devops',   label: 'DevOps' },
  { value: 'planning', label: 'Planning' },
  { value: 'custom',   label: 'Custom' },
] as const

export const CATEGORY_TEMPLATES: Record<string, string> = {
  dev: `# Skill: [Name]

## Purpose
Describe what this skill enables the agent to do.

## Tech Stack Context
- Language:
- Framework:
- Key libraries:

## Coding Standards
- Follow existing file and folder structure
- Write clean, readable code with meaningful names
- Add comments only where logic isn't self-evident

## Branch Naming Convention
- Format: agent/[ticket-id]-[short-description]

## What to avoid
- Do not introduce breaking changes
- Do not modify unrelated files
- Do not add unnecessary dependencies
`,

  qa: `# Skill: [Name]

## Purpose
Describe what testing capabilities this skill provides.

## Test Framework
- Framework:
- Test runner command:
- Coverage tool:

## Testing Standards
- Write unit tests for all new functions
- Write integration tests for API endpoints
- Minimum coverage threshold: 80%

## Test File Conventions
- Location: tests/ or __tests__/
- Naming: [feature].test.[ext]

## What to avoid
- Do not skip flaky tests without documented reason
- Do not mock external services in integration tests
`,

  devops: `# Skill: [Name]

## Purpose
Describe what deployment/infrastructure capabilities this skill provides.

## Environment Config
- Dev branch:
- QA branch:
- Prod branch:

## Deploy Process
1.
2.
3.

## Health Check
- Endpoint:
- Expected response:

## Rollback Procedure
- Steps to roll back a failed deploy:

## What to avoid
- Do not deploy directly to prod without QA sign-off
- Do not modify infrastructure config without approval
`,

  planning: `# Skill: [Name]

## Purpose
Describe what planning and analysis capabilities this skill provides.

## Planning Approach
- Break tickets into atomic tasks
- Estimate effort per task
- Identify dependencies and blockers

## Output Format
Provide a structured sprint plan with:
- Summary of changes
- List of files to create/modify
- Test strategy
- Potential risks

## What to avoid
- Do not over-engineer solutions
- Do not ignore existing patterns in the codebase
`,

  custom: `# Skill: [Name]

## Purpose
Describe what this skill enables the agent to do.

## Guidelines
-

## What to avoid
-
`,
}
