import json
import uuid
from pathlib import Path

from insert_articles import get_resource, insert_articles


def _write_article(directory: Path, slug: str, title: str) -> None:
    (directory / f"{slug}.json").write_text(
        json.dumps(
            {
                "slug": slug,
                "title": title,
                "excerpt": "テスト用の要約",
                "body": "テスト用の本文",
                "category": "FLOURISH",
                "reading_minutes": 3,
                "status": "PUBLISHED",
                "published_at": "2026-08-01T00:00:00Z",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_insert_articles_creates_an_item(tmp_path: Path) -> None:
    slug = f"test-{uuid.uuid4().hex}"
    _write_article(tmp_path, slug, "初回投入")

    insert_articles(tmp_path)

    table = get_resource().Table("flourish_article")
    item = table.get_item(Key={"slug": slug}).get("Item")
    assert item is not None
    assert item["title"] == "初回投入"


def test_insert_articles_is_idempotent_on_rerun(tmp_path: Path) -> None:
    slug = f"test-{uuid.uuid4().hex}"
    _write_article(tmp_path, slug, "初回投入")

    insert_articles(tmp_path)
    insert_articles(tmp_path)

    table = get_resource().Table("flourish_article")
    item = table.get_item(Key={"slug": slug}).get("Item")
    # 同一slugへの複数回の投入は、上書きのみで重複を生まない
    assert item is not None
    assert item["title"] == "初回投入"


def test_insert_articles_reflects_content_changes_on_rerun(tmp_path: Path) -> None:
    slug = f"test-{uuid.uuid4().hex}"
    _write_article(tmp_path, slug, "旧タイトル")
    insert_articles(tmp_path)

    _write_article(tmp_path, slug, "新タイトル")
    insert_articles(tmp_path)

    table = get_resource().Table("flourish_article")
    item = table.get_item(Key={"slug": slug}).get("Item")
    assert item is not None
    assert item["title"] == "新タイトル"


def test_insert_articles_does_not_duplicate_within_category_index(tmp_path: Path) -> None:
    slug = f"test-{uuid.uuid4().hex}"
    _write_article(tmp_path, slug, "初回投入")

    insert_articles(tmp_path)
    insert_articles(tmp_path)

    table = get_resource().Table("flourish_article")
    response = table.query(
        IndexName="category-index",
        KeyConditionExpression="category = :c AND published_at = :p",
        ExpressionAttributeValues={":c": "FLOURISH", ":p": "2026-08-01T00:00:00Z"},
    )
    matches = [it for it in response["Items"] if it["slug"] == slug]
    assert len(matches) == 1
