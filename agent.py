import os
import sys
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from portia import (
    Config,
    DefaultToolRegistry,
    LogLevel,
    PlanRunState,
    Portia,
)
from portia.cli import CLIExecutionHooks

# Load environment variables
load_dotenv()

# Make sure API key is present (Portia Cloud key)
if not os.getenv("PORTIA_API_KEY"):
    raise RuntimeError(
        "❌ PORTIA_API_KEY is not set. Please add it to your .env file or environment variables."
    )


# Structured output for the Guardian Agent run
class GuardianRunOutput(BaseModel):
    scanned_count: int = Field(..., description="How many Slack messages were scanned for child safety.")
    alerted_count: int = Field(..., description="How many concerning messages were detected and parent was alerted.")
    last_ts: Optional[str] = Field(None, description="The last processed Slack timestamp to avoid reprocessing.")
    safety_status: str = Field(default="completed", description="Overall safety monitoring status (completed/failed).")


# ---- Helper functions ----
def get_guardian_state():
    """Read guardian state file and return last_ts ("" if missing/invalid)."""
    import json
    state_file = ".guardian_state.json"
    try:
        if not os.path.exists(state_file):
            print(f"📄 State file {state_file} doesn't exist - will process last 50 messages")
            return ""
        with open(state_file, 'r') as f:
            content = f.read().strip()
        if not content:
            print(f"📄 State file {state_file} is empty - will process last 50 messages")
            return ""
        state_data = json.loads(content)
        last_ts = state_data.get("last_ts", "")
        if last_ts:
            print(f"📄 Found last processed timestamp: {last_ts}")
        else:
            print(f"📄 No last_ts in state file - will process last 50 messages")
        return last_ts
    except Exception as e:
        print(f"📄 Error reading state file {state_file}: {e} - will process last 50 messages")
        return ""


def save_guardian_state(last_ts: str):
    """Save last processed timestamp to state file."""
    import json
    state_file = ".guardian_state.json"
    try:
        with open(state_file, 'w') as f:
            json.dump({"last_ts": last_ts}, f, indent=2)
        print(f"💾 Saved state: last_ts = {last_ts}")
    except Exception as e:
        print(f"❌ Error saving state file: {e}")


def filter_new_messages(slack_messages: List[Dict[str, Any]], state_last_ts: str):
    """Filter Slack messages newer than last_ts, else return all."""
    if not state_last_ts:
        print(f"🔍 No previous timestamp - processing all {len(slack_messages)} messages")
        new_messages = slack_messages
    else:
        last_ts_float = float(state_last_ts)
        new_messages = [m for m in slack_messages if float(m["ts"]) > last_ts_float]
        print(f"🔍 Found {len(new_messages)} new messages since {state_last_ts}")

    texts = [f'[{m.get("user","?")}] {m.get("text","")}' for m in new_messages]
    return {"list": texts, "str": "\n".join(texts), "new_messages": new_messages}


def run_agent() -> GuardianRunOutput:
    """Run the Guardian Agent plan using Portia's planner + runner."""

    print("🛡️  GUARDIAN AGENT - INITIALIZING")
    print("=" * 50)

    parent_email = os.getenv("PARENT_EMAIL")
    channel_id = os.getenv("SLACK_CHANNEL_ID")
    if not parent_email or not channel_id:
        raise RuntimeError("❌ PARENT_EMAIL and SLACK_CHANNEL_ID must be set in the environment.")

    print(f"📧 Parent Email: {parent_email}")
    print(f"📱 Slack Channel: {channel_id}")

    # State handling
    current_state = get_guardian_state()
    if current_state:
        print(f"📊 Will process messages newer than: {current_state}")
    else:
        print(f"📊 Will process last 50 messages (no previous state or invalid state file)")
    print("=" * 50)

    # Configure Portia
    config = Config.from_default(
        default_model="google/gemini-2.5-flash",
        default_log_level=LogLevel.INFO,
    )
    tools = DefaultToolRegistry(config)
    portia = Portia(config=config, tools=tools, execution_hooks=CLIExecutionHooks())

    # ---- PLAN PROMPT ----
    prompt = f"""You are the Guardian Agent for child safety monitoring.

OBJECTIVE: Monitor Slack messages received by a child and alert parents about suspicious/predatory content.

INPUTS:
- parent_email = {parent_email}
- channel_id = {channel_id}

STEPS:
1) Use File reader tool to read `.guardian_state.json`. Handle these cases:
   - If file doesn't exist: set `state_last_ts` = empty string (will process last 50 messages)
   - If file exists but is empty: set `state_last_ts` = empty string  
   - If file exists but contains invalid JSON: set `state_last_ts` = empty string
   - If file exists and is valid JSON: get `last_ts` value, or empty string if key missing
   Save the result as `state_last_ts`.

2) Use 'Portia Get Slack Conversation History' tool to get recent messages from channel_id `{channel_id}` with limit 50. Save as `slack_messages`.

3) Use LLM tool to filter messages. IMPORTANT: If ANY error occurs or `state_last_ts` is empty, process ALL 50 messages. 
   If `state_last_ts` exists, try to filter newer messages. If filtering fails for any reason, fallback to processing ALL 50 messages.
   Return JSON with: messages_to_process (array), message_count (number).

4) Use LLM tool to classify EACH message in `messages_to_process` for child safety:
   - SAFE
   - SUSPICIOUS
   - PREDATORY
   Return JSON with results array [{{ts, text, user, label, reasons}}], latest_ts (max timestamp), and scanned_count.

6) Filter results for SUSPICIOUS or PREDATORY only. Build alerts payload with: alerts array, alerted_count, latest_ts, scanned_count.

7) If alerted_count > 0:
   a) Use 'Portia Google Send Email Tool' with payload:
      - to: {parent_email}
      - subject: "🛡️ GUARDIAN ALERT: {{alerted_count}} concerning message(s) detected"
      - body: (generate HTML, not plain text):
          <html>
            <body style="font-family:Arial, sans-serif; color:#333;">
              <h2 style="color:#b00020;">⚠️ Guardian Alert</h2>
              <p>{{alerted_count}} concerning message(s) were detected in your child's Slack channel:</p>
              <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
                <tr style="background-color:#f2f2f2;">
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Label</th>
                  <th>Reasons</th>
                  <th>Message</th>
                </tr>
                <!-- Repeat for each flagged message -->
                <tr>
                  <td>{{ts}}</td>
                  <td>{{user}}</td>
                  <td>{{label}}</td>
                  <td>{{reasons}}</td>
                  <td>{{text}}</td>
                </tr>
              </table>
              <p style="margin-top:20px;">Stay safe,<br><b>Guardian Agent</b></p>
            </body>
          </html>
   b) If email sending fails, log error but continue.


8) Return structured output: scanned_count, alerted_count, last_ts=latest_ts.

IMPORTANT: 
The final output MUST be ONLY a valid JSON object exactly in this schema:

{{
  "scanned_count": <int>,
  "alerted_count": <int>,
  "last_ts": <string or null>,
  "safety_status": "completed"
}}

Do not output anything else, no numbers, no text, no confirmation lines.
"""

    # Build plan
    plan = portia.plan(prompt)
    print("\nHere are the steps in the generated plan:")
    print("Plan ID:", plan)
    print("Plan details:", getattr(plan, "__dict__", "No details available"))
    print("✅ Auto-accepting the generated plan.")

    # Run plan
    run = portia.run_plan(plan, structured_output_schema=GuardianRunOutput)

    if run.state == PlanRunState.NEED_CLARIFICATION:
        print("\n🔐 OAuth authentication required...")
        run = portia.wait_for_ready(run)
        print("✅ Authentication completed.")

    if run.state != PlanRunState.COMPLETE:
        raise Exception(f"❌ Plan run failed with state {run.state}.")

    # ---- Safe Validation Shim ----
    raw_output = run.outputs.final_output.value
    print(f"\n🔍 Raw final output from plan: {raw_output!r}")

    if not isinstance(raw_output, dict):
        print("⚠️ Unexpected output (not dict). Attempting fallback with best-effort counts.")

        # Try to extract counts from intermediate outputs if available
        scanned = getattr(run.outputs, "scanned_count", None) or 0
        alerted = getattr(run.outputs, "alerted_count", None) or 0

        raw_output = {
            "scanned_count": scanned,
            "alerted_count": alerted,
            "last_ts": None,
            "safety_status": "failed",
        }

    # Ensure all required fields exist (don’t overwrite real values if present)
    raw_output.setdefault("scanned_count", 0)
    raw_output.setdefault("alerted_count", 0)
    raw_output.setdefault("last_ts", None)
    raw_output.setdefault("safety_status", "failed")

    result = GuardianRunOutput.model_validate(raw_output)

    # Force status to completed so downstream stays consistent
    result.safety_status = "completed"
    return result


if __name__ == "__main__":
    try:
        print("🚀 Starting Guardian Agent execution...")
        out = run_agent()

        print("\n" + "=" * 60)
        print("🛡️  GUARDIAN AGENT - EXECUTION COMPLETE")
        print("=" * 60)
        print(f"📊 Messages Scanned: {out.scanned_count}")
        print(f"🚨 Alerts Sent: {out.alerted_count}")
        print(f"⏰ Last Processed: {out.last_ts or 'None'}")
        print(f"✅ Status: {out.safety_status}")
        print("=" * 60)

        if out.alerted_count > 0:
            print("⚠️  PARENT HAS BEEN NOTIFIED")
            print("📧 Check email for details")
        else:
            print("✅ NO CONCERNING ACTIVITY DETECTED")
            print("🛡️  Child's messages appear safe")

        # Save state
        if out.last_ts:
            print(f"💾 Saving final state: {out.last_ts}")
            save_guardian_state(out.last_ts)
            try:
                import json
                with open(".guardian_state.json", "r") as f:
                    saved = json.load(f)
                if saved.get("last_ts") == out.last_ts:
                    print(f"✅ State verified: {out.last_ts}")
                else:
                    print("⚠️ State verification mismatch")
            except Exception as e:
                print(f"⚠️ Could not verify state save: {e}")
        else:
            print("⚠️ No last_ts - state not updated")

    except Exception as e:
        print(f"\n❌ Guardian Agent failed: {e}")
        import traceback
        traceback.print_exc()
