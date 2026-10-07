# Anti Slop: Rules for AI Coding Agents

Anti Slop is a filter, not a style guide: it stops generic AI slop in generated UI, copy, and code, without prescribing aesthetics.

For UI, copy, accessibility, mobile layout, or code comments work, load the matching antislop skill:
- **Core filter (always active)**: `.agents/skills/antislop/SKILL.md`
- **UI / visual**: `.agents/skills/antislop-ui/SKILL.md`
- **Copy & text**: `.agents/skills/antislop-copywriting/SKILL.md`
- **Accessibility & human**: `.agents/skills/antislop-human/SKILL.md`
- **Mobile & responsive**: `.agents/skills/antislop-layoutmobile/SKILL.md`
- **Code comments**: `.agents/skills/antislop-code/SKILL.md`

## Usage Modes
Before starting, follow the core's "Two Usage Modes" section: explicit session instruction first, then global preference, then ask. For a resolved mode, announce `antislop active: <mode> (session override).` or `antislop active: <mode> (global preference).` once, using the actual mode and source. Ask only when no mode is resolved.
