{# © 2026 ShadowStrike. All rights reserved. — Aut Viam Inveniam Aut Faciam
   One writeup's Markdown body, shared by writeup.md and bundle.md. Expects `w` (a WriteupSchema).
   Single-line fields go through md_line, the flag through md_inline_code; approach/notes verbatim. -#}
# {{ w.challenge_name|md_line }}
**CTF:** {{ w.ctf_name|md_line }}
**Category:** {{ w.category }}
**Difficulty:** {{ w.difficulty }}/3
**Date:** {{ w.date }}
**Author:** {{ w.author|md_line }}
{% if w.time_spent_minutes %}**Time spent:** {{ w.time_spent_minutes }} min
{% endif %}
---

## Tools Used
{% for tool in w.tools_used %}- {{ tool|md_line }}
{% else %}_None recorded._
{% endfor %}

## Approach
{{ w.approach }}

## Flag
{{ w.flag|md_line|md_inline_code }}

{% if w.notes %}
## Notes
{{ w.notes }}
{% endif %}
