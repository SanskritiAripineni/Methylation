"""console-v3 (studio): the plain-language interface.

Same engine, same readiness checks, same verdicts as console-v2 - this layer
only changes what a person has to read and click. Where v2 shows a graded
check list, v3 shows one sentence and a button; the check still ran, and a
`fail` still blocks.

Additive over v2:
  * uploads land in a workspace a run can actually be pointed at
    (v2's upload path was inspect-only)
  * run history is read from runs/*/run_record.json, so it survives a restart
  * a measured "time left", from the same per-step medians v2 already keeps
"""
