#!/usr/bin/env bash
# Auswertung eines stream-json-Logs: Tokens je Request für Hauptsitzung und Subagent, Dateizugriffe, Kosten.
set -euo pipefail
f=$1
jq -c -s '
  def tok: .input_tokens + .cache_creation_input_tokens + .cache_read_input_tokens;
  [.[] | select(.type=="assistant")] as $a
  | ($a | map(select(.parent_tool_use_id==null))) as $main
  | ($a | map(select(.parent_tool_use_id!=null))) as $sub
  | ([.[] | select(.type=="assistant") | .message.content[]? | select(.type=="tool_use")]) as $tools
  | {
      main_first: ($main[0].message.usage | tok), main_n: ($main|length), main_sum: ($main | map(.message.usage|tok) | add),
      sub_first: ($sub[0].message.usage | tok // null), sub_n: ($sub|length), sub_sum: ($sub | map(.message.usage|tok) | add // 0),
      sub_peak: ($sub | map(.message.usage|tok) | max // 0),
      sub_models: ($sub | map(.message.model) | unique),
      output_sum: ($a | map(.message.usage.output_tokens) | add),
      skill_calls: ($tools | map(select(.name=="Skill") | .input.skill // .input.command // "?")),
      plugin_reads: ($tools | map(select(.name=="Read") | .input.file_path | select(test("/plugins/"))) | map(sub(".*/plugins/";""))),
      agent_calls: ($tools | map(select(.name=="Agent") | .input.subagent_type)),
      cost_usd: ([.[] | select(.type=="result")][0].total_cost_usd), duration_s: (([.[] | select(.type=="result")][0].duration_ms)/1000|floor),
      result_head: ([.[] | select(.type=="result")][0].result | .[0:160])
    }' "$f"
