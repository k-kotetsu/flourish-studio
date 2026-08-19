"""ARTICLEテーブルから公開サイト（S-01 トップページ / K-01 記事一覧 / K-02 記事詳細）の
静的HTMLを生成する。

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
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import boto3

from insert_articles import TABLE_NAME, Article, get_resource

SITE_DIR = Path(__file__).resolve().parent / "site_assets"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "dist" / "site"
LEGAL_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs" / "14_法務文書"

AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
PUBLIC_SITE_BUCKET_NAME = os.environ.get("PUBLIC_SITE_BUCKET_NAME")
CLOUDFRONT_DISTRIBUTION_ID = os.environ.get("CLOUDFRONT_DISTRIBUTION_ID")
# api/app/core/config.pyのPUBLIC_DOMAIN_NAMEと同じ環境変数名（絶対URLの組み立てに使う）。
# 未設定時はOGP/canonical/sitemap.xmlを省略し、ローカル出力のみ行う
# （PUBLIC_SITE_BUCKET_NAME等と同じ「未設定ならローカルのみ」の方針）。
PUBLIC_DOMAIN_NAME = os.environ.get("PUBLIC_DOMAIN_NAME")

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

# S-01専用のアイコン。線画・24pxグリッド・currentColor（flourish-uiスキル「アイコン」）。
CHECK_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M4 12.5 9 17.5 20 6.5"/></svg>'
)
TOP_FEATURE_ICONS = {
    "report": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M4 20V9M9.5 20V4M15 20v-7M20.5 20v-4"/></svg>'
    ),
    "map": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="3.5" r="1.6"/>'
        '<circle cx="20.5" cy="12" r="1.6"/><circle cx="12" cy="20.5" r="1.6"/>'
        '<circle cx="3.5" cy="12" r="1.6"/>'
        '<path d="M12 9V5.1M15 12h3.9M12 15v3.9M9 12H5.1"/></svg>'
    ),
    "week": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>'
    ),
}

# Flourish Mapの構造図（ヒーロー。wireframe-spec 7.1.1「1 ヒーロー」）。
TOP_ART_MAP = (
    '<svg viewBox="0 0 320 190" fill="none" stroke="currentColor" stroke-width="1.4" '
    'stroke-linecap="round" role="img" '
    'aria-label="ありたい姿を中心に、Career・Financial・Physical・Social'
    'の4領域がつながる構造図">'
    '<circle cx="160" cy="95" r="27" fill="var(--primary-soft)" '
    'stroke="currentColor" stroke-width="1.6"/>'
    '<text x="160" y="92" text-anchor="middle" font-size="11" fill="var(--text)" '
    'stroke="none" font-weight="700">ありたい姿</text>'
    '<text x="160" y="105" text-anchor="middle" font-size="8" fill="var(--text-sub)" '
    'stroke="none">3〜5年後</text>'
    '<path d="M160 68V34M187 95h46M160 122v34M133 95H87" '
    'stroke-dasharray="3 4" opacity=".7"/>'
    '<g stroke-width="1.4">'
    '<rect x="121" y="10" width="78" height="24" rx="12" fill="var(--surface)"/>'
    '<text x="160" y="26" text-anchor="middle" font-size="11" fill="var(--text)" '
    'stroke="none">Career</text>'
    '<rect x="233" y="83" width="80" height="24" rx="12" fill="var(--surface)"/>'
    '<text x="273" y="99" text-anchor="middle" font-size="11" fill="var(--text)" '
    'stroke="none">Financial</text>'
    '<rect x="121" y="156" width="78" height="24" rx="12" fill="var(--surface)"/>'
    '<text x="160" y="172" text-anchor="middle" font-size="11" fill="var(--text)" '
    'stroke="none">Physical</text>'
    '<rect x="7" y="83" width="80" height="24" rx="12" fill="var(--surface)"/>'
    '<text x="47" y="99" text-anchor="middle" font-size="11" fill="var(--text)" '
    'stroke="none">Social</text>'
    "</g>"
    "</svg>"
)

# 成長の4段階の図（Flourishとは。wireframe-spec 7.1.1「3 Flourishとは」）。
TOP_ART_GROW = (
    '<svg viewBox="0 0 320 120" fill="none" stroke="currentColor" stroke-width="1.4" '
    'stroke-linecap="round" stroke-linejoin="round" role="img" '
    'aria-label="種・芽・苗・木と育っていく成長の4段階の図">'
    '<path d="M14 100h292" stroke="var(--border)" stroke-width="1.4"/>'
    '<g opacity=".45">'
    '<ellipse cx="46" cy="90" rx="7" ry="9"/><path d="M46 99v-9"/>'
    '<text x="46" y="116" text-anchor="middle" font-size="10" fill="var(--text-sub)" '
    'stroke="none">種</text>'
    "</g>"
    '<g opacity=".6">'
    '<path d="M122 100V78"/>'
    '<path d="M122 78c0-9-6-15-15-15 0 9 6 15 15 15z"/>'
    '<path d="M122 82c0-7 5-12 12-12 0 7-5 12-12 12z"/>'
    '<text x="122" y="116" text-anchor="middle" font-size="10" fill="var(--text-sub)" '
    'stroke="none">芽</text>'
    "</g>"
    '<g opacity=".8">'
    '<path d="M198 100V56"/>'
    '<path d="M198 70c0-11-8-18-19-18 0 11 8 18 19 18z"/>'
    '<path d="M198 78c0-11 8-18 19-18 0 11-8 18-19 18z"/>'
    '<text x="198" y="116" text-anchor="middle" font-size="10" fill="var(--text-sub)" '
    'stroke="none">苗</text>'
    "</g>"
    "<g>"
    '<path d="M274 100V64"/>'
    '<circle cx="274" cy="42" r="24" fill="var(--primary-soft)"/>'
    '<path d="M274 64V34M274 48l-11-11M274 54l12-12"/>'
    '<text x="274" y="116" text-anchor="middle" font-size="10" fill="var(--text)" '
    'stroke="none" font-weight="700">木</text>'
    "</g>"
    "</svg>"
)

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


def _og_tags(title: str, description: str, path: str, domain_name: str | None, og_type: str) -> str:
    """OGP・canonicalタグ。絶対URLが要るため、ドメインが分かるビルドでのみ出力する
    （`PUBLIC_DOMAIN_NAME`未設定のローカル出力では省略する）。
    """
    if not domain_name:
        return ""
    url = f"https://{domain_name}{path}"
    return f"""
    <link rel="canonical" href="{url}" />
    <meta property="og:type" content="{og_type}" />
    <meta property="og:site_name" content="Flourish Studio" />
    <meta property="og:title" content="{html.escape(title)}" />
    <meta property="og:description" content="{html.escape(description)}" />
    <meta property="og:url" content="{url}" />
    <meta name="twitter:card" content="summary" />"""


def _page_head(
    title: str,
    description: str,
    path: str,
    domain_name: str | None,
    *,
    og_type: str = "website",
) -> str:
    return f"""<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
{THEME_INIT_SCRIPT}
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="{html.escape(description)}" />
    <title>{html.escape(title)}</title>{_og_tags(title, description, path, domain_name, og_type)}
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
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


# ロゴマーク(P7-3、`web/src/domain/logo.ts`の`LOGO_MARK_PATHS`と同じ双葉のモチーフ)。
# TypeScript側と定義が分かれるのは`growth_stage.py`/`growthStage.ts`と同じ既存パターン。
_LOGO_MARK_PATHS = (
    '<path d="M12 21V10"/>'
    '<path d="M12 13c0-4-3-6.5-7-6.5 0 4 3 6.5 7 6.5z"/>'
    '<path d="M12 15c0-4 3-6.5 7-6.5 0 4-3 6.5-7 6.5z"/>'
    '<path d="M8 21h8"/>'
)
_LOGO_MARK_SVG = (
    '<svg class="site-header__brand-mark" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
    f'stroke-linejoin="round" aria-hidden="true">{_LOGO_MARK_PATHS}</svg>'
)


def _top_header() -> str:
    return f"""    <header class="site-header">
      <span class="site-header__brand">{_LOGO_MARK_SVG}Flourish Studio</span>
      <a class="site-header__action" href="/app/s-02">ログイン</a>
    </header>"""


# ログイン済みでS-01へアクセスした場合はS-41へ自動遷移する
# （screen-list.md「S-01 トップページ」例外）。
TOP_AUTH_SCRIPT = """    <script>
      (function () {
        fetch("/api/v1/me", { credentials: "include" })
          .then(function (res) {
            if (res.ok) {
              location.replace("/app/s-41");
            }
          })
          .catch(function () {
            /* 未到達時はトップページの表示のまま */
          });
      })();
    </script>"""


def _vow_item(text: str) -> str:
    return (
        f'        <li class="lp-vow"><span class="lp-vow__check">{CHECK_ICON}</span>'
        f"<span>{text}</span></li>"
    )


def _feat_card(icon: str, heading: str, body: str) -> str:
    return f"""        <li class="lp-feat">
          <span class="lp-feat__icon">{icon}</span>
          <div class="lp-feat__body">
            <h3 class="lp-feat__heading">{html.escape(heading)}</h3>
            <p class="lp-feat__text">{html.escape(body)}</p>
          </div>
        </li>"""


def _step_item(number: int, heading: str, body: str) -> str:
    return f"""        <li class="lp-step">
          <span class="lp-step__number">{number}</span>
          <div class="lp-step__body">
            <h3 class="lp-step__heading">{html.escape(heading)}</h3>
            <p class="lp-step__text">{html.escape(body)}</p>
          </div>
        </li>"""


def render_top_page(articles: list[Article], domain_name: str | None) -> str:
    """S-01 トップページ。7セクション＋読みもの＋フッターの縦長スクロール
    （wireframe-spec 7.1.1）。**アプリ画面ではなくウェブサイト**として、
    Vue SPA（/app/*）とは別に静的サイトジェネレータで生成する。
    """
    domain_cards = "\n".join(
        _feat_card(CATEGORY_ICONS[category], label, description)
        for category, label, description in (
            ("CAREER", "Career", "仕事、働き方、成長、役割"),
            ("FINANCIAL", "Financial", "収入、支出、貯蓄、資産形成、生活設計"),
            ("PHYSICAL", "Physical", "健康、体力、睡眠、運動、生活習慣"),
            ("SOCIAL", "Social", "人間関係、家族、友人、社会とのつながり"),
        )
    )

    feature_cards = "\n".join(
        _feat_card(icon, heading, body)
        for icon, heading, body in (
            (
                TOP_FEATURE_ICONS["report"],
                "いまの自分を知る",
                "4つの領域について答えると、AIが今の状態を文章で整理します。"
                "点数はつけません。満たされている点と、気になっている点の両方をお返しします。",
            ),
            (
                TOP_FEATURE_ICONS["map"],
                "ありたい姿を、地図にする",
                "AIとの対話を通じて、3〜5年後のありたい姿を自分の言葉にします。"
                "そこから4つの領域それぞれの理想の状態と、今年の目標へつなげます。",
            ),
            (
                TOP_FEATURE_ICONS["week"],
                "週に一度、振り返る",
                "毎日の記録は求めません。週に一度だけ、目標の進み方を選ぶと、"
                "AIが振り返り・気づき・次の一歩を整理します。",
            ),
        )
    )

    steps = "\n".join(
        _step_item(number, heading, body)
        for number, heading, body in (
            (
                1,
                "5分の質問に答える",
                "登録は不要です。4つの領域について、いまの気持ちに近いものを選んでいきます。",
            ),
            (
                2,
                "いまの自分を受け取る",
                "AIが整理した現在地を、その場で全部お見せします。ここまで無料で、登録もいりません。",
            ),
            (
                3,
                "ありたい姿をつくる",
                "続けたくなったら登録して、AIと話しながら3〜5年後の姿を言葉にしていきます。",
            ),
            (
                4,
                "少しずつ育てる",
                "4つの領域を一度に埋める必要はありません。ひとつずつ、週に一度の振り返りで育てていきます。",
            ),
        )
    )

    noticing_vows = "\n".join(
        _vow_item(text)
        for text in (
            "大きな不満はないのに、<b>何となく満たされない</b>",
            "将来が不安。でも<b>何が不安なのか説明できない</b>",
            "転職も、貯金も、運動も。<b>やることが多くて手がつかない</b>",
            "理想の状態を<b>自分の言葉にできていない</b>",
        )
    )

    values_vows = "\n".join(
        _vow_item(text)
        for text in (
            "<b>何も売りません。</b>AIとの対話や目標の提案に、広告や商品への誘導を混ぜません。",
            "<b>点数をつけません。</b>優劣ではなく、言葉になった度合いと行動の積み重ねを見ます。",
            "<b>答えを押しつけません。</b>AIは考えを引き出す伴走者です。決めるのはいつもあなたです。",
            "<b>書き換わることを歓迎します。</b>1年後に考えが変わっていても、それは失敗ではなく成長です。",
        )
    )

    reading_cards = "\n".join(
        (
            f'      <a class="article-card" href="/articles/{html.escape(article["slug"])}">\n'
            f'        <span class="article-card__thumb">'
            f'{CATEGORY_ICONS[article["category"]]}</span>\n'
            f'        <span class="article-card__body">\n'
            f'          <span class="article-card__meta">'
            f'{html.escape(CATEGORY_LABELS[article["category"]])}</span>\n'
            f'          <span class="article-card__title">'
            f'{html.escape(article["title"])}</span>\n'
            f'          <span class="article-card__excerpt">'
            f'{html.escape(article["excerpt"])}</span>\n'
            f"        </span>\n"
            f"      </a>"
        )
        for article in articles[:3]
    )

    body = f"""
{_top_header()}
    <main class="lp-main">
      <section class="lp-section lp-hero">
        <div class="lp-section__inner">
          <p class="lp-eyebrow">Wellbeing Platform</p>
          <h1 class="lp-hero__heading">
            人生は、<br />完成させるものじゃない。<br />育てていくものだ。
          </h1>
          <p class="lp-hero__lead">
            <b>自分の現在地を知り、自分なりのより良い人生を探索し、育てていく。</b><br />
            Flourish Studio は、そのためのパーソナルスタジオです。
          </p>
          <div class="lp-illustration">{TOP_ART_MAP}</div>
          <p class="lp-note">20〜30代のキャリア形成期に。何かを売ることはありません。</p>
        </div>
      </section>

      <section class="lp-section lp-section--tint">
        <div class="lp-section__inner">
          <p class="lp-eyebrow">こんな状態、ありませんか</p>
          <ul class="lp-vow-list">
{noticing_vows}
          </ul>
          <p class="lp-note">
            世の中のサービスの多くは、困りごとを自覚している人向けにできています。
            まだ言葉になっていない段階の人が、置いていかれがちでした。
          </p>
        </div>
      </section>

      <section class="lp-section">
        <div class="lp-section__inner">
          <p class="lp-eyebrow">Flourish とは</p>
          <h2 class="lp-section__heading">自分らしく、よりよく生き、<br />成長している状態。</h2>
          <p class="lp-body">
            Flourish とは、人生のさまざまな側面が良い状態にあり、その人らしく力を発揮しながら、
            成長し、充実して生きている状態のことです。
          </p>
          <div class="lp-illustration">{TOP_ART_GROW}</div>
          <p class="lp-body">
            大事なのは、いま楽かどうかではありません。たとえば仕事が大変で、
            一時的に幸福感が低かったとしても——自分にとって意味のある仕事をしている。
            成長している。良い仲間がいる。将来に向かって進んでいる。
            そう感じられているなら、<b>Flourishing は高い</b>と言えます。
          </p>
          <p class="lp-quote">3年後のあなたを、1枚の地図に。</p>
        </div>
      </section>

      <section class="lp-section lp-section--tint">
        <div class="lp-section__inner">
          <p class="lp-eyebrow">4つの領域</p>
          <h2 class="lp-section__heading">
            仕事も、お金も、からだも、つながりも。<br />バラバラの悩みじゃなかった。
          </h2>
          <p class="lp-body">
            Flourish Studio が扱う4つの領域は、ギャラップ社が示した
            ウェルビーイングの構成要素をもとにしています。
          </p>
          <ul class="lp-feat-list">
{domain_cards}
          </ul>
          <p class="lp-body">
            この4つを別々の悩みとして扱うのではなく、ひとつの「ありたい姿」に紐づけて構造化する。
            そうやって自分を見つめ直すことで、<b>人生全体が良い方向に機能し、成長し、充実していく</b>ことを支えます。
          </p>
          <p class="lp-note">
            なぜ働き方を変えたいのか。なぜ貯蓄したいのか。なぜ健康を整えたいのか。
            なぜ人とのつながりを大切にしたいのか。それらはすべて、ひとつの姿につながっています。
          </p>
        </div>
      </section>

      <section class="lp-section">
        <div class="lp-section__inner">
          <p class="lp-eyebrow">できること</p>
          <h2 class="lp-section__heading">3つの機能で、<br />人生を育てていきます。</h2>
          <ul class="lp-feat-list">
{feature_cards}
          </ul>
        </div>
      </section>

      <section class="lp-section lp-section--tint">
        <div class="lp-section__inner">
          <p class="lp-eyebrow">はじめかた</p>
          <ol class="lp-steps">
{steps}
          </ol>
        </div>
      </section>

      <section class="lp-section">
        <div class="lp-section__inner">
          <p class="lp-eyebrow">大切にしていること</p>
          <ul class="lp-vow-list">
{values_vows}
          </ul>
        </div>
      </section>

      <section class="lp-section lp-section--tint">
        <div class="lp-section__inner lp-section__inner--wide">
          <p class="lp-eyebrow">読みもの</p>
          <h2 class="lp-section__heading">人生を育てるための、<br />知識とヒント。</h2>
          <div class="article-grid">
{reading_cards}
          </div>
          <a class="lp-link-more" href="/articles">記事をもっと見る</a>
        </div>
      </section>

      <footer class="lp-footer">
        <p class="lp-note">© Flourish Studio ／ <a href="/terms-of-service">利用規約</a> ／
          <a href="/privacy-policy">プライバシーポリシー</a></p>
      </footer>
    </main>

    <div class="lp-cta">
      <a class="lp-cta__button" href="/app/s-11">5分で、いまの自分を見てみる</a>
      <p class="lp-cta__note">登録はあとからで大丈夫です</p>
    </div>
{TOP_AUTH_SCRIPT}
  </body>
</html>
"""
    top_description = (
        "自分の現在地を知り、自分なりのより良い人生を探索し、育てていく。"
        "Flourish Studio は、そのためのパーソナルスタジオです。何も売らないAI。"
    )
    return _page_head("Flourish Studio", top_description, "/", domain_name) + body


def render_article_list_page(articles: list[Article], domain_name: str | None) -> str:
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
    return _page_head("記事 | Flourish Studio", list_description, "/articles", domain_name) + body


def render_article_detail_page(article: Article, domain_name: str | None) -> str:
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
    path = f"/articles/{article['slug']}"
    return (
        _page_head(
            f"{article['title']} | Flourish Studio",
            article["excerpt"],
            path,
            domain_name,
            og_type="article",
        )
        + body
    )


def render_robots_txt(domain_name: str | None) -> str:
    """`/app/*`（要ログインのSPA）・`/api/*`は集客対象ではないため巡回対象から外す
    （`11_技術構成`2章「公開サイトとアプリを分ける」理由：LPと記事はSEOが要る）。
    """
    lines = ["User-agent: *", "Allow: /", "Disallow: /app/", "Disallow: /api/"]
    if domain_name:
        lines += ["", f"Sitemap: https://{domain_name}/sitemap.xml"]
    return "\n".join(lines) + "\n"


def render_sitemap(articles: list[Article], domain_name: str | None) -> str | None:
    """sitemap.xmlの`<loc>`は絶対URLが要るため、ドメインが分かるビルドでのみ生成する。"""
    if not domain_name:
        return None

    paths_with_lastmod: list[tuple[str, str | None]] = [
        ("/", None),
        ("/articles", None),
        ("/privacy-policy", None),
        ("/terms-of-service", None),
    ]
    paths_with_lastmod += [
        (f"/articles/{article['slug']}", article["published_at"][:10]) for article in articles
    ]

    entries = []
    for path, lastmod in paths_with_lastmod:
        lastmod_tag = f"\n    <lastmod>{lastmod}</lastmod>" if lastmod else ""
        loc = f"https://{domain_name}{path}"
        entries.append(f"  <url>\n    <loc>{loc}</loc>{lastmod_tag}\n  </url>")

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )


_TASK_REFERENCE = re.compile(r"（P\d+-\d+[^）]*）")


def _inline_md(text: str) -> str:
    """`**太字**`と`` `コード` ``のみを扱う、この2文書専用の最小限のインラインMarkdown変換。"""
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)


def _render_legal_body(markdown_text: str) -> tuple[str, str]:
    """`docs/14_法務文書/`の法務文書（P7-1）をHTMLに変換する。

    この2文書に十分な範囲（見出しh2・テーブル・箇条書き・段落・太字・コード）だけを
    扱う専用の最小限のパーサ（汎用Markdownライブラリは導入しない）。
    冒頭のバージョン管理メタデータ（1つ目の"---"まで）は内部向けのため出力しない。
    1つ目と2つ目の"---"の間にある注記(blockquote)は、内部タスクID
    （例："（P7-9 本番デプロイ）"）を取り除いたうえで注記として表示する。
    """
    lines = markdown_text.split("\n")
    title = lines[0].removeprefix("# ").strip()

    first_rule = lines.index("---")
    second_rule = lines.index("---", first_rule + 1)
    notice = " ".join(
        line.strip().removeprefix("> ")
        for line in lines[first_rule + 1 : second_rule]
        if line.strip().startswith("> ")
    )
    notice = _TASK_REFERENCE.sub("", notice).strip()

    parts: list[str] = []
    if notice:
        parts.append(f'<p class="legal-notice">{_inline_md(notice)}</p>')

    list_buffer: list[str] = []
    table_buffer: list[str] = []

    def flush_list() -> None:
        if list_buffer:
            items = "\n".join(f"<li>{_inline_md(item)}</li>" for item in list_buffer)
            parts.append(f"<ul>\n{items}\n</ul>")
            list_buffer.clear()

    def flush_table() -> None:
        if table_buffer:
            rows = [
                [cell.strip() for cell in row.strip().strip("|").split("|")]
                for row in table_buffer
            ]
            header, _separator, *data_rows = rows
            head_cells = "".join(f"<th>{_inline_md(cell)}</th>" for cell in header)
            body_rows = "\n".join(
                "<tr>" + "".join(f"<td>{_inline_md(cell)}</td>" for cell in row) + "</tr>"
                for row in data_rows
            )
            parts.append(f"<table><thead><tr>{head_cells}</tr></thead><tbody>\n{body_rows}\n</tbody></table>")
            table_buffer.clear()

    for line in lines[second_rule + 1 :]:
        stripped = line.rstrip()
        if not stripped:
            flush_list()
            flush_table()
        elif stripped.startswith("## "):
            flush_list()
            flush_table()
            parts.append(f"<h2>{_inline_md(stripped.removeprefix('## '))}</h2>")
        elif stripped.startswith("|"):
            table_buffer.append(stripped)
        elif stripped.startswith("- "):
            flush_table()
            list_buffer.append(stripped.removeprefix("- "))
        else:
            flush_list()
            flush_table()
            parts.append(f"<p>{_inline_md(stripped)}</p>")
    flush_list()
    flush_table()

    return title, "\n".join(parts)


def render_legal_page(markdown_text: str, path: str, domain_name: str | None) -> str:
    title, body_html = _render_legal_body(markdown_text)
    body = f"""
{_header(title, "/")}
    <main class="site-main">
      <article class="article">
        <h1 class="article__title">{html.escape(title)}</h1>
        <div class="article__body">
{body_html}
        </div>
      </article>
    </main>
{AUTH_SWITCH_SCRIPT}
  </body>
</html>
"""
    description = f"Flourish Studioの{title}。"
    return _page_head(f"{title} | Flourish Studio", description, path, domain_name) + body


def fetch_published_articles() -> list[Article]:
    table = get_resource().Table(TABLE_NAME)
    items = cast("list[Article]", table.scan()["Items"])
    published = [item for item in items if item["status"] == "PUBLISHED"]
    published.sort(key=lambda a: a["published_at"], reverse=True)
    return published


def build_site(
    output_dir: Path = OUTPUT_DIR, domain_name: str | None = PUBLIC_DOMAIN_NAME
) -> list[Article]:
    """`output_dir`直下に生成する。S3キーとローカルのファイル名は必ずしも一致しない
    （S3では"articles"というオブジェクトと"articles/xxx"というオブジェクトが共存できるが、
    ローカルのファイルシステムではファイルとディレクトリが同名で共存できないため）。
    対応関係は`_iter_upload_targets`にまとめる。
    """
    articles = fetch_published_articles()

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(
        render_top_page(articles, domain_name), encoding="utf-8"
    )
    (output_dir / "articles_list.html").write_text(
        render_article_list_page(articles, domain_name), encoding="utf-8"
    )

    detail_dir = output_dir / "articles_detail"
    detail_dir.mkdir(parents=True, exist_ok=True)
    for article in articles:
        (detail_dir / article["slug"]).write_text(
            render_article_detail_page(article, domain_name), encoding="utf-8"
        )

    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "site.css").write_text(
        (SITE_DIR / "site.css").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (output_dir / "favicon.svg").write_text(
        (SITE_DIR / "favicon.svg").read_text(encoding="utf-8"), encoding="utf-8"
    )

    (output_dir / "privacy_policy.html").write_text(
        render_legal_page(
            (LEGAL_DOCS_DIR / "privacy-policy.md").read_text(encoding="utf-8"),
            "/privacy-policy",
            domain_name,
        ),
        encoding="utf-8",
    )
    (output_dir / "terms_of_service.html").write_text(
        render_legal_page(
            (LEGAL_DOCS_DIR / "terms-of-service.md").read_text(encoding="utf-8"),
            "/terms-of-service",
            domain_name,
        ),
        encoding="utf-8",
    )

    (output_dir / "robots.txt").write_text(render_robots_txt(domain_name), encoding="utf-8")
    sitemap = render_sitemap(articles, domain_name)
    if sitemap is not None:
        (output_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    print(f"{len(articles)}件の記事をもとに静的サイトを {output_dir} に生成しました。")
    return articles


def _iter_upload_targets(output_dir: Path) -> list[tuple[Path, str, str]]:
    """(ローカルパス, S3キー, Content-Type) の一覧。

    記事一覧・記事詳細はいずれも拡張子なしのキーで配置する（"/articles"、
    "/articles/{slug}"というURLとS3キーを一致させ、CloudFrontのdefaultRootObjectの
    挙動に頼らないため）。
    """
    targets: list[tuple[Path, str, str]] = [
        (output_dir / "index.html", "index.html", "text/html; charset=utf-8"),
        (output_dir / "articles_list.html", "articles", "text/html; charset=utf-8"),
        (output_dir / "assets" / "site.css", "assets/site.css", "text/css; charset=utf-8"),
        (output_dir / "favicon.svg", "favicon.svg", "image/svg+xml"),
        (output_dir / "robots.txt", "robots.txt", "text/plain; charset=utf-8"),
        (output_dir / "privacy_policy.html", "privacy-policy", "text/html; charset=utf-8"),
        (output_dir / "terms_of_service.html", "terms-of-service", "text/html; charset=utf-8"),
    ]
    sitemap_path = output_dir / "sitemap.xml"
    if sitemap_path.exists():
        targets.append((sitemap_path, "sitemap.xml", "application/xml; charset=utf-8"))
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
    paths = [
        "/",
        "/articles",
        "/articles/*",
        "/robots.txt",
        "/sitemap.xml",
        "/favicon.svg",
        "/privacy-policy",
        "/terms-of-service",
    ]
    cloudfront = boto3.client("cloudfront")
    cloudfront.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {"Quantity": len(paths), "Items": paths},
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
