"""Structural fingerprints exclude values and expanding period columns."""
import hashlib
import json
import re


def strict_json_loads(content):
    """Reject duplicate JSON object keys, including duplicated observation periods."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(content, object_pairs_hook=unique_object)


def schema_fingerprint(obj) -> str:
    def shape(value):
        if isinstance(value, dict):
            fields = {}
            for key, item in value.items():
                name = '<period>' if re.fullmatch(r'\d{4}-(?:M\d{2}|Q[1-4])', key) else key
                fields.setdefault(name, set()).add(json.dumps(shape(item), sort_keys=True))
            return {k: sorted(v) for k, v in sorted(fields.items())}
        if isinstance(value, list):
            return sorted({json.dumps(shape(v), sort_keys=True) for v in value})
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return 'number'
        return type(value).__name__
    return hashlib.sha256(json.dumps(shape(obj), sort_keys=True).encode()).hexdigest()
