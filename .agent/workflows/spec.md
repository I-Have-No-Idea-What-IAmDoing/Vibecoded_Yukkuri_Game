---
description: Systematically refine strict technical specifications from rough ideas through an agent-led interview process.
---

# Deep-Dive Spec Interview

**Purpose**: To systematically refine strict technical specifications from rough ideas through an agent-led interview process.

## How to Use

1. **Create a Spec File**
   Create a markdown file (e.g., in a `specs/` directory) with your rough idea.
   Example: `specs/my-feature.md` with "Let's build X".

2. **Trigger the Interview**
   Run the slash command pointing to your file:
   `/spec @specs/my-feature.md`

## The Interview Loop

The agent will pause and interview you in rounds, covering:

- **Core Mechanics**: What does it actually do?
- **User Experience**: How does it feel/look?
- **Technical Architecture**: Stack, data, security.
- **Edge Cases**: Error handling, offline states, race conditions.

## Final Output

The agent rewrites your original file into a comprehensive, implementation-ready specification document.

## Why use this?

- **Prevents ambiguity**: Forces decisions on "obvious" things that aren't actually obvious.
- **Saves dev time**: Coding against a strict spec is much faster than guessing.
- **Documents decisions**: The final spec serves as the source of truth for the project.
