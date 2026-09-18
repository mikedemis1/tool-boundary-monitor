# Exported audit schema

Decision and outcome records share this validated schema. Decision durations are null.
Outcome gateway time covers normalization through decision flush/admission, excluding native execution and final audit writing. Tool time covers the native call only.
Rate/sequence scores are null and detectors are not evaluated. Source references are observed, not causal.

```json
{
  "$defs": {
    "SourceReference": {
      "additionalProperties": false,
      "properties": {
        "kind": {
          "const": "tool_result",
          "title": "Kind",
          "type": "string"
        },
        "tool_name": {
          "title": "Tool Name",
          "type": "string"
        },
        "event_id": {
          "title": "Event Id",
          "type": "string"
        },
        "trust": {
          "const": "untrusted_content",
          "title": "Trust",
          "type": "string"
        }
      },
      "required": [
        "kind",
        "tool_name",
        "event_id",
        "trust"
      ],
      "title": "SourceReference",
      "type": "object"
    }
  },
  "additionalProperties": false,
  "properties": {
    "schema_version": {
      "const": "tbm.m1.v1",
      "title": "Schema Version",
      "type": "string"
    },
    "event_type": {
      "enum": [
        "decision",
        "outcome"
      ],
      "title": "Event Type",
      "type": "string"
    },
    "event_id": {
      "title": "Event Id",
      "type": "string"
    },
    "request_id": {
      "title": "Request Id",
      "type": "string"
    },
    "pending_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Pending Id"
    },
    "run_id": {
      "title": "Run Id",
      "type": "string"
    },
    "case_id": {
      "title": "Case Id",
      "type": "string"
    },
    "configuration": {
      "enum": [
        "none",
        "scopes",
        "hard"
      ],
      "title": "Configuration",
      "type": "string"
    },
    "principal_id": {
      "title": "Principal Id",
      "type": "string"
    },
    "agent_id": {
      "title": "Agent Id",
      "type": "string"
    },
    "task_run_id": {
      "title": "Task Run Id",
      "type": "string"
    },
    "session_id": {
      "title": "Session Id",
      "type": "string"
    },
    "task_class": {
      "title": "Task Class",
      "type": "string"
    },
    "policy_version": {
      "title": "Policy Version",
      "type": "string"
    },
    "grant_version": {
      "title": "Grant Version",
      "type": "string"
    },
    "sequence_position": {
      "minimum": 0,
      "title": "Sequence Position",
      "type": "integer"
    },
    "state_version": {
      "minimum": 0,
      "title": "State Version",
      "type": "integer"
    },
    "tool_name": {
      "title": "Tool Name",
      "type": "string"
    },
    "tool_risk": {
      "enum": [
        "read",
        "write"
      ],
      "title": "Tool Risk",
      "type": "string"
    },
    "required_scopes": {
      "items": {
        "type": "string"
      },
      "title": "Required Scopes",
      "type": "array"
    },
    "granted_scopes": {
      "items": {
        "type": "string"
      },
      "title": "Granted Scopes",
      "type": "array"
    },
    "observed_sources": {
      "items": {
        "$ref": "#/$defs/SourceReference"
      },
      "title": "Observed Sources",
      "type": "array"
    },
    "causal_influence": {
      "const": "unknown",
      "title": "Causal Influence",
      "type": "string"
    },
    "decision": {
      "enum": [
        "allow",
        "shadow",
        "approve",
        "block"
      ],
      "title": "Decision",
      "type": "string"
    },
    "reason_codes": {
      "items": {
        "type": "string"
      },
      "title": "Reason Codes",
      "type": "array"
    },
    "checked_layers": {
      "items": {
        "type": "string"
      },
      "title": "Checked Layers",
      "type": "array"
    },
    "authorized": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "title": "Authorized"
    },
    "execution_status": {
      "enum": [
        "not_executed",
        "succeeded",
        "tool_error",
        "audit_incomplete"
      ],
      "title": "Execution Status",
      "type": "string"
    },
    "gateway_duration_ns": {
      "anyOf": [
        {
          "minimum": 0,
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "title": "Gateway Duration Ns"
    },
    "tool_duration_ns": {
      "anyOf": [
        {
          "minimum": 0,
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "title": "Tool Duration Ns"
    },
    "rate_score": {
      "title": "Rate Score",
      "type": "null"
    },
    "sequence_score": {
      "title": "Sequence Score",
      "type": "null"
    },
    "detector_status": {
      "const": "not_evaluated",
      "title": "Detector Status",
      "type": "string"
    },
    "error_code": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Error Code"
    },
    "argument_fingerprint": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Argument Fingerprint"
    },
    "effect_fingerprint": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Effect Fingerprint"
    },
    "resource_fingerprints": {
      "items": {
        "type": "string"
      },
      "title": "Resource Fingerprints",
      "type": "array"
    }
  },
  "required": [
    "schema_version",
    "event_type",
    "event_id",
    "request_id",
    "pending_id",
    "run_id",
    "case_id",
    "configuration",
    "principal_id",
    "agent_id",
    "task_run_id",
    "session_id",
    "task_class",
    "policy_version",
    "grant_version",
    "sequence_position",
    "state_version",
    "tool_name",
    "tool_risk",
    "required_scopes",
    "granted_scopes",
    "observed_sources",
    "causal_influence",
    "decision",
    "reason_codes",
    "checked_layers",
    "authorized",
    "execution_status",
    "gateway_duration_ns",
    "tool_duration_ns",
    "rate_score",
    "sequence_score",
    "detector_status",
    "error_code",
    "argument_fingerprint",
    "effect_fingerprint",
    "resource_fingerprints"
  ],
  "title": "Event",
  "type": "object"
}
```
