"""ARTICLEテーブルから公開サイト（K-01 記事一覧 / K-02 記事詳細）の静的HTMLを生成する。

真実の源は `flourish_article` テーブル（08_データモデル6章、11_技術構成4.4）。
ビルド時にDBを読んでHTMLを出力し、S3へ配置したうえでCloudFrontのキャッシュを
invalidationする。DBは公開経路から外れ、公開サイトの表示はDBの状態に依存しない。

ログイン状態によるヘッダー・CTAバナーの出し分け（wireframe-spec 7.1.2）は、
静的HTML自体には焼き込まず、`GET /api/v1/me` の成否をクライアントJSで見て
`data-auth` 属性を切り替える。これによりHTMLはDBにもセッションにも依存しない。
"""

from __future__ import annotations

import html
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import boto3

from insert_articles import TABLE_NAME, Article, get_resource

SITE_DIR = Path(__file__).resolve().parent / "site_assets"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "dist" / "site"

AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
PUBLIC_SITE_BUCKET_NAME = os.environ.get("PUBLIC_SITE_BUCKET_NAME")
CLOUDFRONT_DISTRIBUTION_ID = os.environ.get("CLOUDFRONT_DISTRIBUTION_ID")

CATEGORIES = ["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL", "FLOURISH"]
CATEGORY_LABELS = {
    "CAREER": "Career",
    "FINANCIAL": "Financial",
    "PHYSICAL": "Physical",
    "SOCIAL": "Social",
    "FLOURISH": "Flourishとは",
}

# 線画のみ・線幅1.6px・24pxグリッド・色はcurrentColor（flourish-uiスキル「アイコン」）。
CATEGORY_ICONS = {
    "CAREER": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<rect x="3" y="8" width="18" height="12" rx="2"/>'
        '<path d="M8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        '<path d="M3 13h18"/></svg>'
    ),
    "FINANCIAL": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<circle cx="12" cy="12" r="8"/>'
        '<path d="M12 7v10M9.3 9.6c0-1.1 1.2-1.9 2.7-1.9s2.7.8 2.7 1.8-1.1 1.5-2.7 1.6'
        '-2.7.7-2.7 1.9 1.2 1.8 2.7 1.8 2.7-.7 2.7-1.8"/></svg>'
    ),
    "PHYSICAL": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M3 12h4l2-6 4 12 2-6h6"/></svg>'
    ),
    "SOCIAL": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<circle cx="9" cy="8" r="3"/>'
        '<path d="M4 20c0-3.3 2.2-5.5 5-5.5s5 2.2 5 5.5"/>'
        '<circle cx="17" cy="8" r="2.5"/>'
        '<path d="M15.3 14.7c2.4.3 3.9 2.4 3.9 5.3"/></svg>'
    ),
    "FLOURISH": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M12 21c-5-1-8-5-8-10 5 0 9 3 10 8"/>'
        '<path d="M12 21c5-1 8-5 8-10-5 0-9 3-10 8"/>'
        '<path d="M12 21V9"/></svg>'
    ),
}

# ちらつき防止（web/index.htmlと同じキー・同じロジック。07_デザイン原則3.3）。
THEME_INIT_SCRIPT = """    <script>
      (function () {
        try {
          var stored = localStorage.getItem("flourish-theme");
          if (stored === "light" || stored === "dark") {
            document.documentElement.setAttribute("data-theme", stored);
          }
        } catch (e) {
          /* localStorage不可（プライベートモード等）。自動追従にフォールバック */
        }
      })();
    </script>"""

# ログイン状態の出し分け（wireframe-spec 7.1.2）。DBにもセッションにも依存しないよう、
# 生成後のHTMLは常に「未登録」の見た目で出し、`GET /api/v1/me` の成否だけで切り替える。
AUTH_SWITCH_SCRIPT = """    <script>
      (function () {
        fetch("/api/v1/me", { credentials: "include" })
          .then(function (res) {
            if (!res.ok) return;
            document.querySelectorAll('[data-auth="signed-out"]').forEach(function (el) {
              el.hidden = true;
            });
            document.querySelectorAll('[data-auth="signed-in"]').forEach(function (el) {
              el.hidden = false;
            });
          })
          .catch(function () {
            /* 未到達時は未登録向けの表示のまま */
          });
      })();
    </script>"""

LIST_PAGE_SIZE = 6

LIST_INTERACTION_SCRIPT = f"""    <script>
      (function () {{
        var PAGE_SIZE = {LIST_PAGE_SIZE};
        var cards = Array.prototype.slice.call(document.querySelectorAll(".article-card"));
        var chips = Array.prototype.slice.call(document.querySelectorAll(".chip"));
        var loadMoreBtn = document.querySelector(".load-more");
        var currentCategory = "ALL";
        var visibleCount = PAGE_SIZE;

        function matches(card) {{
          return currentCategory === "ALL" || card.dataset.category === currentCategory;
        }}

        function render() {{
          var matched = cards.filter(matches);
          matched.forEach(function (card, i) {{
            card.hidden = i >= visibleCount;
          }});
          cards.filter(function (c) {{ return !matches(c); }}).forEach(function (c) {{
            c.hidden = true;
          }});
          loadMoreBtn.hidden = matched.length <= visibleCount;
        }}

        chips.forEach(function (chip) {{
          chip.addEventListener("click", function () {{
            chips.forEach(function (c) {{ c.classList.remove("is-selected"); }});
            chip.classList.add("is-selected");
            currentCategory = chip.dataset.category;
            visibleCount = PAGE_SIZE;
            render();
          }});
        }});

        loadMoreBtn.addEventListener("click", function () {{
          visibleCount += PAGE_SIZE;
          render();
        }});

        render();
      }})();
    </script>"""


def _format_date(published_at: str) -> str:
    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    return f"{dt.year}.{dt.month}.{dt.day}"


def _page_head(title: str, description: str) -> str:
    return f"""<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
{THEME_INIT_SCRIPT}
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="{html.escape(description)}" />
    <title>{html.escape(title)}</title>
    <link rel="stylesheet" href="/assets/site.css" />
  </head>
  <body>"""


def _header(title: str, back_href: str) -> str:
    return f"""    <header class="site-header">
      <a class="site-header__nav" href="{back_href}" aria-label="戻る">‹ 戻る</a>
      <span class="site-header__title">{html.escape(title)}</span>
      <a class="site-header__action" href="/app/s-02" data-auth="signed-out">ログイン</a>
      <a class="site-header__action" href="/app/s-41" data-auth="signed-in" hidden>ホーム</a>
    </header>"""


def _cta_banner() -> str:
    return """    <div class="cta-banner" data-auth="signed-out">
      <p class="cta-banner__lead">ここまで読んでみて、浮かんだことはありますか。</p>
      <a class="cta-banner__button" href="/app/s-11">5分で、いまの自分を見てみる</a>
      <p class="cta-banner__note">登録はあとからで大丈夫です</p>
    </div>"""


def render_article_list_page(articles: list[Article]) -> str:
    chips = [
        '      <button type="button" class="chip is-selected" data-category="ALL">'
        "すべて</button>"
    ]
    for category in CATEGORIES:
        chips.append(
            f'      <button type="button" class="chip" data-category="{category}">'
            f"{html.escape(CATEGORY_LABELS[category])}</button>"
        )

    cards = []
    for article in articles:
        category = article["category"]
        slug = html.escape(article["slug"])
        meta = (
            f"{html.escape(CATEGORY_LABELS[category])} ・ "
            f"{_format_date(article['published_at'])} ・ "
            f"{article['reading_minutes']}分"
        )
        cards.append(
            f"""      <a class="article-card" href="/articles/{slug}" data-category="{category}">
        <span class="article-card__thumb">{CATEGORY_ICONS[category]}</span>
        <span class="article-card__body">
          <span class="article-card__meta">{meta}</span>
          <span class="article-card__title">{html.escape(article["title"])}</span>
          <span class="article-card__excerpt">{html.escape(article["excerpt"])}</span>
        </span>
      </a>"""
        )

    body = f"""
{_header("記事", "/")}
    <main class="site-main">
      <h1 class="site-heading">読みもの</h1>
      <div class="chip-row" role="group" aria-label="カテゴリで絞り込む">
{chr(10).join(chips)}
      </div>
      <div class="article-grid">
{chr(10).join(cards)}
      </div>
      <button type="button" class="load-more">もっと読む</button>
    </main>
{AUTH_SWITCH_SCRIPT}
{LIST_INTERACTION_SCRIPT}
  </body>
</html>
"""
    list_description = (
        "Flourish Studioの読みもの。CareerやFinancialなど4つの領域と、"
        "Flourishという考え方について。"
    )
    return _page_head("記事 | Flourish Studio", list_description) + body


def render_article_detail_page(article: Article) -> str:
    paragraphs = "\n".join(
        f"        <p>{html.escape(paragraph)}</p>"
        for paragraph in article["body"].split("\n\n")
        if paragraph.strip()
    )
    category = article["category"]
    meta = (
        f"{html.escape(CATEGORY_LABELS[category])} ・ "
        f"{_format_date(article['published_at'])} ・ "
        f"{article['reading_minutes']}分"
    )
    body = f"""
{_header(CATEGORY_LABELS[category], "/articles")}
    <main class="site-main">
      <article class="article">
        <p class="article__meta">{meta}</p>
        <h1 class="article__title">{html.escape(article["title"])}</h1>
        <div class="article__body">
{paragraphs}
        </div>
{_cta_banner()}
      </article>
    </main>
{AUTH_SWITCH_SCRIPT}
  </body>
</html>
"""
    return _page_head(f"{article['title']} | Flourish Studio", article["excerpt"]) + body


def fetch_published_articles() -> list[Article]:
    table = get_resource().Table(TABLE_NAME)
    items = cast("list[Article]", table.scan()["Items"])
    published = [item for item in items if item["status"] == "PUBLISHED"]
    published.sort(key=lambda a: a["published_at"], reverse=True)
    return published


def build_site(output_dir: Path = OUTPUT_DIR) -> list[Article]:
    """`output_dir`直下に生成する。S3キーとローカルのファイル名は必ずしも一致しない
    （S3では"articles"というオブジェクトと"articles/xxx"というオブジェクトが共存できるが、
    ローカルのファイルシステムではファイルとディレクトリが同名で共存できないため）。
    対応関係は`_iter_upload_targets`にまとめる。
    """
    articles = fetch_published_articles()

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "articles_list.html").write_text(
        render_article_list_page(articles), encoding="utf-8"
    )

    detail_dir = output_dir / "articles_detail"
    detail_dir.mkdir(parents=True, exist_ok=True)
    for article in articles:
        (detail_dir / article["slug"]).write_text(
            render_article_detail_page(article), encoding="utf-8"
        )

    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "site.css").write_text(
        (SITE_DIR / "site.css").read_text(encoding="utf-8"), encoding="utf-8"
    )

    print(f"{len(articles)}件の記事をもとに静的サイトを {output_dir} に生成しました。")
    return articles


def _iter_upload_targets(output_dir: Path) -> list[tuple[Path, str, str]]:
    """(ローカルパス, S3キー, Content-Type) の一覧。

    記事一覧・記事詳細はいずれも拡張子なしのキーで配置する（"/articles"、
    "/articles/{slug}"というURLとS3キーを一致させ、CloudFrontのdefaultRootObjectの
    挙動に頼らないため）。
    """
    targets: list[tuple[Path, str, str]] = [
        (output_dir / "articles_list.html", "articles", "text/html; charset=utf-8"),
        (output_dir / "assets" / "site.css", "assets/site.css", "text/css; charset=utf-8"),
    ]
    for path in sorted((output_dir / "articles_detail").iterdir()):
        targets.append((path, f"articles/{path.name}", "text/html; charset=utf-8"))
    return targets


def sync_to_s3(output_dir: Path, bucket_name: str) -> None:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    for local_path, key, content_type in _iter_upload_targets(output_dir):
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=local_path.read_bytes(),
            ContentType=content_type,
        )
    print(f"{bucket_name} へ同期しました。")


def invalidate_cloudfront(distribution_id: str) -> None:
    cloudfront = boto3.client("cloudfront")
    cloudfront.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {"Quantity": 2, "Items": ["/articles", "/articles/*"]},
            "CallerReference": datetime.now(UTC).isoformat(),
        },
    )
    print(f"{distribution_id} のキャッシュをinvalidationしました。")


def publish_site() -> None:
    build_site()
    if not PUBLIC_SITE_BUCKET_NAME:
        print("PUBLIC_SITE_BUCKET_NAME が未設定のため、ローカル出力のみ行いました。")
        return

    sync_to_s3(OUTPUT_DIR, PUBLIC_SITE_BUCKET_NAME)

    if not CLOUDFRONT_DISTRIBUTION_ID:
        print("CLOUDFRONT_DISTRIBUTION_ID が未設定のため、invalidationは行いませんでした。")
        return

    invalidate_cloudfront(CLOUDFRONT_DISTRIBUTION_ID)


if __name__ == "__main__":
    publish_site()
