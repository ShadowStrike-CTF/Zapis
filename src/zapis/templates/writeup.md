# {{ challenge_name }}
**CTF:** {{ ctf_name }}
**Category:** {{ category }}
**Difficulty:** {{ difficulty }}/3
**Date:** {{ date }}
**Author:** {{ author }}

---

## Tools Used
{% for tool in tools_used %}- {{ tool }}
{% endfor %}

## Approach
{{ approach }}

## Flag
`{{ flag }}`

{% if notes %}
## Notes
{{ notes }}
{% endif %}
