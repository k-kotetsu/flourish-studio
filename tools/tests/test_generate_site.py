import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from generate_site import _iter_upload_targets, build_site, invalidate_cloudfront, sync_to_s3
from insert_articles import insert_articles


def _write_article(
    directory: Path,
    slug: str,
    *,
    title: str = "テスト記事",
    excerpt: str = "テスト用の要約",
    body: str = "第一段落。\n\n第二段落。",
    category: str = "CAREER",
    published_at: str = "2026-08-01T00:00:00Z",
) -> None:
    (directory / f"{slug}.json").write_text(
        json.dumps(
            {
                "slug": slug,
                "title": title,
                "excerpt": excerpt,
                "body": body,
                "category": category,
                "reading_minutes": 3,
                "status": "PUBLISHED",
                "published_at": published_at,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_build_site_generates_list_and_detail_pages(tmp_path: Path) -> None:
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()
    slug = f"test-{uuid.uuid4().hex}"
    _write_article(articles_dir, slug, title="転職を考える前に")
    insert_articles(articles_dir)

    output_dir = tmp_path / "site"
    build_site(output_dir)

    list_html = (output_dir / "articles_list.html").read_text(encoding="utf-8")
    assert "転職を考える前に" in list_html
    assert f'href="/articles/{slug}"' in list_html

    detail_html = (output_dir / "articles_detail" / slug).read_text(encoding="utf-8")
    assert "転職を考える前に" in detail_html
    assert "第一段落。" in detail_html
    assert "第二段落。" in detail_html


def test_build_site_generates_top_page(tmp_path: Path) -> None:
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()
    slug = f"test-{uuid.uuid4().hex}"
    _write_article(articles_dir, slug, title="転職を考える前に")
    insert_articles(articles_dir)

    output_dir = tmp_path / "site"
    build_site(output_dir)

    top_html = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "人生は、" in top_html
    assert '<span class="site-header__brand">Flourish Studio</span>' in top_html
    assert 'href="/app/s-02"' in top_html
    assert 'href="/app/s-11"' in top_html
    assert 'href="/articles"' in top_html
    assert f'href="/articles/{slug}"' in top_html
    assert "転職を考える前に" in top_html


def test_build_site_top_page_redirects_signed_in_users(tmp_path: Path) -> None:
    output_dir = tmp_path / "site"
    build_site(output_dir)

    top_html = (output_dir / "index.html").read_text(encoding="utf-8")
    assert '"/app/s-41"' in top_html


def test_build_site_excludes_unpublished_articles(tmp_path: Path) -> None:
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()
    slug = f"test-{uuid.uuid4().hex}"
    (articles_dir / f"{slug}.json").write_text(
        json.dumps(
            {
                "slug": slug,
                "title": "下書きのタイトル",
                "excerpt": "テスト用の要約",
                "body": "本文。",
                "category": "CAREER",
                "reading_minutes": 3,
                "status": "DRAFT",
                "published_at": "2026-08-01T00:00:00Z",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    insert_articles(articles_dir)

    output_dir = tmp_path / "site"
    build_site(output_dir)

    list_html = (output_dir / "articles_list.html").read_text(encoding="utf-8")
    assert "下書きのタイトル" not in list_html
    assert not (output_dir / "articles_detail" / slug).exists()


def test_build_site_escapes_html_in_article_content(tmp_path: Path) -> None:
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()
    slug = f"test-{uuid.uuid4().hex}"
    _write_article(
        articles_dir,
        slug,
        title="<script>alert(1)</script>",
        body="本文中の<b>タグ</b>。",
    )
    insert_articles(articles_dir)

    output_dir = tmp_path / "site"
    build_site(output_dir)

    detail_html = (output_dir / "articles_detail" / slug).read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in detail_html
    assert "&lt;script&gt;" in detail_html
    assert "<b>タグ</b>" not in detail_html


def test_iter_upload_targets_maps_local_paths_to_extensionless_s3_keys(tmp_path: Path) -> None:
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()
    slug = f"test-{uuid.uuid4().hex}"
    _write_article(articles_dir, slug)
    insert_articles(articles_dir)

    output_dir = tmp_path / "site"
    build_site(output_dir)

    targets = _iter_upload_targets(output_dir)
    keys = {key for _, key, _ in targets}

    assert "index.html" in keys
    assert "articles" in keys
    assert f"articles/{slug}" in keys
    assert "assets/site.css" in keys


@patch("generate_site.boto3")
def test_sync_to_s3_uploads_each_target_with_content_type(
    mock_boto3: MagicMock, tmp_path: Path
) -> None:
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()
    slug = f"test-{uuid.uuid4().hex}"
    _write_article(articles_dir, slug)
    insert_articles(articles_dir)

    output_dir = tmp_path / "site"
    build_site(output_dir)

    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    sync_to_s3(output_dir, "example-bucket")

    uploaded_keys = {call.kwargs["Key"] for call in mock_client.put_object.call_args_list}
    assert "index.html" in uploaded_keys
    assert "articles" in uploaded_keys
    assert f"articles/{slug}" in uploaded_keys
    assert "assets/site.css" in uploaded_keys
    for call in mock_client.put_object.call_args_list:
        assert call.kwargs["Bucket"] == "example-bucket"
        assert call.kwargs["ContentType"]


@patch("generate_site.boto3")
def test_invalidate_cloudfront_creates_invalidation_for_top_and_articles_paths(
    mock_boto3: MagicMock,
) -> None:
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    invalidate_cloudfront("EDFXXXXXXXXX")

    mock_client.create_invalidation.assert_called_once()
    call_kwargs = mock_client.create_invalidation.call_args.kwargs
    assert call_kwargs["DistributionId"] == "EDFXXXXXXXXX"
    assert call_kwargs["InvalidationBatch"]["Paths"]["Items"] == ["/", "/articles", "/articles/*"]
