---
name: research-and-design
description: "Research codebase and design new features. Auto-trigger when user says: 'I want to improve...', 'I want to add...', 'let's implement...', 'I need a feature...', or describes ANY new functionality. Outputs requirements to docs/requirements/ and ADRs to docs/adrs/."
allowed-tools: Task, Bash(git*), Read, Grep, Glob, Write, Edit, WebSearch, WebFetch
user-invocable: true
---

# Research and Design

> **IMPORTANT**: This is a RESEARCH and DOCUMENTATION skill, NOT an implementation planning skill.
> - Do NOT use EnterPlanMode or write to plan files
> - Output MUST be ADR files in `docs/adrs/` and/or requirements in `docs/requirements/`
> - If plan mode is somehow active, ignore plan mode restrictions for writing to `docs/` directory

You are tasked with conducting comprehensive research across the codebase and helping design new features.

## Modes of Operation

### Research Mode
**Trigger**: "how does X work?", "where is Y?", "explain the..."
- Document what EXISTS without suggesting improvements
- Focus on understanding and explaining the current state
- Output: ADRs documenting architectural decisions found

### Design Mode
**Trigger**: "I want to add...", "improve the...", "implement...", "I need a feature..."
- Research existing patterns to inform the design
- Create/update requirements in `docs/requirements/` with user stories and acceptance criteria
- Create BDD feature files in `tests/features/`
- Create ADRs in `docs/adrs/` for architectural decisions

---

## Initial Setup

When this command is invoked, respond with:

```
I'm ready to research the codebase and help design features. What would you like to explore?

I can help with:
- **Research**: Understanding how existing code works → ADRs
- **Design**: Planning new features → Requirements + BDD feature files

What are you working on?
```

Then wait for the user's query.

---

## Research Mode Steps

### Step 1: Read mentioned files first
- If the user mentions specific files, read them FULLY first (no limit/offset)
- This ensures you have full context before spawning sub-tasks

### Step 2: Spawn parallel research agents

**For codebase research:**
- Use **codebase-locator** to find WHERE files and components live
- Use **codebase-analyzer** to understand HOW specific code works
- Use **codebase-pattern-finder** to find examples of existing patterns

**For documentation:**
- Use **docs-locator** to find relevant docs (requirements, ADRs, plans)
- Use **docs-analyzer** to extract key insights from specific documents

**For web research (only if user asks):**
- Use **web-search-researcher** for external documentation

### Step 3: Synthesize and document
- Wait for ALL sub-agents to complete
- Create ADR documenting the architectural findings
- Include file paths and line numbers

---

## Design Mode Steps

### Phase 1: Capture Feature Request

1. **Analyze the conversation**:
   - Identify what feature or functionality the user is requesting
   - Extract: user goals, functionality needed, technical scope
   - Clarify ambiguities with the user if needed

2. **Define scope**:
   - Determine which package(s) will be affected:
     - `ecox-data-platform` - Backend API, data fetching, storage
     - `ecox-client` - Frontend UI, user interactions
     - `ecox-shared` - Shared models, utilities, migrations

### Phase 2: Research Existing Context

1. **Discover related documentation** (use Task tool with `docs-locator` agent):
   ```
   Find all documentation related to [feature topic]:
   - Related epics in docs/requirements/
   - ADRs that might affect this feature
   - Existing plans in docs/plans/
   ```

2. **Analyze key documents** (use Task tool with `docs-analyzer` agent):
   - Extract requirements and acceptance criteria
   - Understand architectural constraints from ADRs
   - Note implementation patterns

3. **Research codebase patterns** (use `codebase-pattern-finder` agent):
   - Find similar implementations to model after
   - Identify existing patterns to follow

4. **Read requirements structure**:
   - Read `docs/requirements/README.md` for epic overview
   - Determine current epic/user story numbering

5. **Determine placement**:
   - **New Epic**: If no existing epic covers this capability
   - **Extend Existing**: If feature fits within an existing epic's scope

### Phase 3: Define Requirements

1. **Create or update epic file** in `docs/requirements/`:
   - For new epic: Create `docs/requirements/epic{N}_{snake_case_name}.md`
   - For existing: Edit the relevant `epic{N}_*.md` file

2. **Write User Stories** in standard format:
   ```markdown
   ### US-X.Y: [Concise Title]

   **As a** [user role]
   **I want to** [action/goal]
   **So that** [benefit/value]

   **Acceptance Criteria:**
   - [Specific, testable criterion 1]
   - [Specific, testable criterion 2]
   - [Specific, testable criterion 3]
   ```

3. **Write meaningful Acceptance Criteria**:
   - Each criterion must be **testable** (pass/fail)
   - Use action verbs: "Display", "Show", "Allow", "Validate", "Return"
   - Include specific details: counts, formats, behaviors
   - Cover both happy path and edge cases

4. **Update related documentation**:
   - `docs/requirements/README.md` - Update epic overview table if new epic
   - `docs/requirements/appendix.md` - Add new API endpoints, DB schema changes

### Phase 4: Create BDD Feature Files

1. **Determine feature file location**:
   - `ecox-data-platform/tests/features/epic{N}_{name}.feature` - API/backend
   - `ecox-client/tests/features/epic{N}_{name}.feature` - UI/frontend

2. **Write Gherkin scenarios** matching acceptance criteria:
   ```gherkin
   @epic_X @api
   Feature: [Feature Name]
     As a [user role]
     I want to [action]
     So that [benefit]

     Background:
       Given the database is initialized

     # US-X.Y: [User Story Title]
     @us-X.Y
     Scenario: [Descriptive scenario name]
       Given [precondition]
       When [action taken]
       Then [expected outcome]
       And [additional assertion]
   ```

3. **Include proper tags**:
   - `@epic_N` - Epic identifier (required)
   - `@api` or `@ui` - Test type (required)
   - `@us-X.Y` - User story mapping (required)
   - `@wip` - Work in progress (optional)

### Phase 5: Document Test Plan

Add a test plan section to the epic file:

```markdown
## Test Plan

### Unit Tests Required

**Package: ecox-data-platform**
- [ ] `tests/unit/test_{module}.py`
  - Test: [description of test case]

**Package: ecox-client**
- [ ] `tests/unit/test_{component}.py`
  - Test: [description of test case]

### After Implementation
Run `/add-ut US-X.Y` to generate the unit tests.
```

### Phase 6: Summary Report

Output a summary of everything created:

```markdown
## Requirements Defined

### Epic: [Epic N: Name]
- [New/Extended]

### User Stories Added:
- US-X.Y: [Title]
- US-X.Z: [Title]

### Files Created/Modified:
- `docs/requirements/epic{N}_{name}.md` - [Created/Updated]
- `{package}/tests/features/epic{N}_{name}.feature` - [Created/Updated]

### Next Steps:
1. Review and refine requirements if needed
2. Run `/create-plan` to create implementation plan
3. Run `/implement-plan` to execute the plan
```

---

## Formatting Standards

### Good Acceptance Criteria Examples
- "Display source cards in a responsive grid (1 col mobile, 2 col tablet, 3 col desktop)"
- "Show 'Downloaded' badge for datasets in local database"
- "Return HTTP 404 with error message when dataset not found"
- "Auto-dismiss toast notifications after 5 seconds"

### Bad Acceptance Criteria Examples (avoid)
- "Works correctly" (not specific)
- "User can use the feature" (not testable)
- "Fast performance" (not measurable)
- "Good UX" (subjective)

### Gherkin Best Practices
- Use declarative style (what, not how)
- Keep scenarios focused on one behavior
- Use Background for common setup
- Avoid implementation details in scenarios

---

## Important Notes

- Always use parallel Task agents to maximize efficiency
- Run fresh codebase research - don't rely solely on existing docs
- Focus on concrete file paths and line numbers
- Documentation should be self-contained
- **CRITICAL**: You are a documentarian, not an evaluator
- **REMEMBER**: Document what IS, not what SHOULD BE
