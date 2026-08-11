from app.ai.schema import to_wire_schema


def test_to_wire_schema_strips_unsupported_keywords() -> None:
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "minLength": 1, "maxLength": 60},
            "items": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {"type": "string", "minLength": 1},
            },
        },
        "required": ["message", "items"],
        "additionalProperties": False,
    }

    wire = to_wire_schema(schema)

    assert "minLength" not in wire["properties"]["message"]
    assert "maxLength" not in wire["properties"]["message"]
    assert "minItems" not in wire["properties"]["items"]
    assert "maxItems" not in wire["properties"]["items"]
    assert "minLength" not in wire["properties"]["items"]["items"]
    # 表現できる制約はそのまま残る
    assert wire["type"] == "object"
    assert wire["required"] == ["message", "items"]
    assert wire["additionalProperties"] is False


def test_to_wire_schema_does_not_mutate_the_original() -> None:
    schema = {"type": "string", "minLength": 1}

    to_wire_schema(schema)

    assert schema == {"type": "string", "minLength": 1}
