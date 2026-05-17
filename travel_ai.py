"""
旅行提案アプリ（Streamlit・1ファイル版）

OpenAI API（Chat Completions）で旅先をゼロベース提案します。
API キーは .env の OPENAI_API_KEY で管理してください（.env.example 参照）。
"""

from __future__ import annotations

import json
import os
import random

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# 背景画像: Picsum Photos（フリー・高速 CDN、seed で URL が安定）
# https://picsum.photos/

# ---------------------------------------------------------------------------
# OpenAI API で旅行先をゼロベース提案（固定候補リストは使わない）
# ---------------------------------------------------------------------------
# APIキーはプロジェクト直下の .env に OPENAI_API_KEY=sk-... の形式で保存する。
# python-dotenv で読み込む（travel_ai.py と同じディレクトリの .env を想定）。
load_dotenv()

# カード左上の絵文字（APIの JSON には含めず、こちらで割り当て）
_CARD_EMOJIS: tuple[str, ...] = ("✈️", "🧳", "🌏")

# OpenAI に返してもらう JSON の形（プロンプトと画面表示の両方で参照）
# キー名は _normalize_one_destination で読むので、ここを変えたらそちらも合わせること
_JSON_SHAPE_USER_HINT = """
【出力フォーマット（厳守）】
次の構造の JSON オブジェクトだけを返してください。余計な説明文やマークダウンは不要です。
{
  "destinations": [
    {
      "name": "おすすめの旅先（国・地域を含めて具体的に）",
      "reason": "おすすめ理由。ユーザーの予算・日数・テーマにどう合うかを、自然な日本語で2〜5文程度で書くこと。",
      "description": "どんなところか（情景が浮かぶ短文でも可）",
      "atmosphere": "その土地の空気感",
      "recommended_for": "どんな人・旅スタイルに向いているか",
      "experience_hints": "現地での体験のヒント",
      "price_estimate": "料金の目安（概算。航空券は別途の旨を海外なら明記）"
    }
  ]
}
destinations は必ずちょうど 3 件にしてください。
"""


def _build_subtitle(
    theme_text: str, budget_man: int, trip_days: int, season: str
) -> str:
    """カード下部に表示する「今回の条件」一行サマリー。"""
    t = (theme_text or "").strip().replace("\n", " ")
    if len(t) > 80:
        t = t[:77] + "…"
    return (
        f"【今回の条件】{trip_days}日・予算目安 {budget_man}万円・{season}・テーマ：{t or '（未入力）'}"
    )


def _normalize_one_destination(raw: dict, index: int) -> dict[str, str]:
    """
    API が返した辞書を1件、UI が期待するキーに正規化する。

    API のキー名とアプリ内部キーの対応（初心者向けメモ）:
    - reason → pitch_reason（カードで「おすすめ理由」として最上段に表示）
    - description → pitch_lead（「どんなところか」）
    """
    name = str(raw.get("name", "")).strip() or f"候補 {index + 1}"
    # おすすめ理由: モデルが別キーで返した場合も拾う
    reason = str(
        raw.get("reason", "") or raw.get("recommendation_reason", "") or ""
    ).strip()
    desc = str(raw.get("description", "")).strip()
    if not reason and desc:
        # 古いプロンプト互換: reason が無いときは description を理由欄に回す
        reason = desc
        desc = ""
    atm = str(raw.get("atmosphere", "")).strip()
    rec = str(raw.get("recommended_for", "")).strip()
    xp = str(raw.get("experience_hints", "")).strip()
    price = str(raw.get("price_estimate", "")).strip()
    emoji = _CARD_EMOJIS[index % len(_CARD_EMOJIS)]
    return {
        "name": name,
        "tag": "AI提案",
        "emoji": emoji,
        "pitch_reason": reason,
        "pitch_lead": desc,
        "pitch_atmosphere": atm,
        "pitch_for_who": rec,
        "pitch_experiences": xp,
        "price_estimate": price,
    }


def fetch_travel_suggestions_openai(
    theme_text: str,
    budget_man: int,
    trip_days: int,
    season: str,
) -> tuple[list[dict[str, str]], str | None]:
    """
    OpenAI Chat Completions で JSON を受け取り、ちょうど3件の旅先を返す。

    Returns:
        (suggestions, error_message)
        成功時 error_message は None。
    """
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return [], "環境変数 OPENAI_API_KEY が空です。プロジェクト直下の .env に設定してください。"

    user_block = f"""以下の条件で、日本在住の旅行者向けにおすすめの旅先を **3つ** 提案してください。
固定の候補リストから選ぶ必要はありません。日本国内・海外どこでも構いません。

■旅行テーマ（自由記述）
{theme_text.strip() or "（特になし／おまかせ）"}

■予算の目安
およそ {budget_man} 万円（現地での滞在に使えるイメージ。航空券は別枠で考えてよい）

■旅行日数
{trip_days} 日（往復の移動日を含む全体の日程）

■いつ頃行きたいか
{season}

各候補について必ず「reason」（おすすめ理由）を充実させ、
ユーザーの予算・日数・テーマがなぜその旅先に合うのかを自然な文章でつなげてください。
文体は「旅行好きがワクワクする」トーンで。単なる観光地説明にせず、情景と体験が浮かぶように書いてください。
"""

    # OpenAI 公式の Python SDK（openai パッケージ）でクライアントを作る
    # キーは引数でも渡せるが、ここでは .env 読み込み済みの環境変数を明示的に渡している
    client = OpenAI(api_key=api_key)
    try:
        # response_format で JSON モードにすると、返答が JSON になりやすい（パースしやすい）
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "あなたは旅行情報に強いアシスタントです。"
                        "ユーザーの条件に合わせ、具体的な地名を含む旅先を3件提案します。"
                        "必ず有効な JSON だけを返し、キー名は指定どおり英語で揃えてください。"
                    ),
                },
                {
                    "role": "user",
                    "content": user_block + "\n" + _JSON_SHAPE_USER_HINT,
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.85,
        )
    except Exception as e:
        return [], f"OpenAI API の呼び出しに失敗しました: {e}"

    raw_text = (completion.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        return [], f"JSON の解析に失敗しました: {e}\n---\n{raw_text[:500]}"

    arr = data.get("destinations")
    if not isinstance(arr, list):
        arr = data.get("suggestions") or data.get("places")
    if not isinstance(arr, list):
        return [], "JSON に destinations 配列がありません。"

    subtitle = _build_subtitle(theme_text, budget_man, trip_days, season)
    out: list[dict[str, str]] = []
    for i, row in enumerate(arr[:3]):
        if not isinstance(row, dict):
            continue
        item = _normalize_one_destination(row, i)
        item["subtitle"] = subtitle
        out.append(item)

    if len(out) < 3:
        return [], f"有効な候補が {len(out)} 件しかありませんでした。APIの応答を確認してください。"

    return out, None


def fallback_demo_cards(
    theme_text: str, budget_man: int, trip_days: int, season: str, err: str
) -> list[dict[str, str]]:
    """
    API が使えないときのプレースホルダー（.env 未設定や通信エラー時）。
    カードグリッドが3列なので、同じレイアウトになるよう3枚分返す。
    """
    sub = _build_subtitle(theme_text, budget_man, trip_days, season)
    return [
        {
            "name": "まずは API キーを設定",
            "tag": "セットアップ",
            "emoji": "🔧",
            "pitch_reason": err,
            "pitch_lead": "",
            "pitch_atmosphere": "プロジェクト直下に `.env` を作成し、`OPENAI_API_KEY=` のあとにキーを貼り付けて保存します。",
            "pitch_for_who": "OpenAI のアカウントから API キーを発行してください（課金設定は各自の責任でお願いします）。",
            "pitch_experiences": "`.env.example` をコピーして `.env` にリネームするのが手早いです。",
            "price_estimate": "（API 未接続）",
            "subtitle": sub,
        },
        {
            "name": "依存パッケージをインストール",
            "tag": "セットアップ",
            "emoji": "📦",
            "pitch_reason": "Python のライブラリが未インストールのときに表示されます。",
            "pitch_lead": "ターミナルでこのフォルダに移動し、次を実行してください。",
            "pitch_atmosphere": "`pip install -r requirements.txt`",
            "pitch_for_who": "仮想環境（venv）を使うと他の Python プロジェクトと干渉しにくくなります。",
            "pitch_experiences": "インストール後に `streamlit run travel_ai.py` で起動します。",
            "price_estimate": "（API 未接続）",
            "subtitle": sub,
        },
        {
            "name": "もう一度ボタンを押す",
            "tag": "セットアップ",
            "emoji": "🔄",
            "pitch_reason": "設定が終わったら、もう一度メインのボタンから AI に依頼してください。",
            "pitch_lead": "キーとパッケージが揃ったら、同じ条件でもう一度「AI に提案」を押してください。",
            "pitch_atmosphere": "エラー内容が変われば、あと一歩で直ることが多いです。",
            "pitch_for_who": "ファイアウォールや社内ネットで api.openai.com がブロックされていないかも確認ください。",
            "pitch_experiences": "それでもダメなときは、エラーメッセージ全文をコピーして調べると原因が特定しやすいです。",
            "price_estimate": "（API 未接続）",
            "subtitle": sub,
        },
    ]


def _session_landscape_wallpaper_url() -> str:
    """セッションごとに seed を 1 つ決め、Picsum の画像 URL に変換する。"""
    if "wallpaper_seed" not in st.session_state:
        st.session_state.wallpaper_seed = random.randint(1, 999_999_999)
    # リクエスト時にリダイレクトせず静的パスで配信されやすい形式
    return (
        f"https://picsum.photos/seed/{st.session_state.wallpaper_seed}/1920/1080"
    )


def inject_landscape_background(image_url: str) -> None:
    """
    背景: 写真を主役に鮮明表示し、ごく薄い blur（端のチラつき抑制）と
    弱い縦方向グラデのみでコントラストを整える（重い黒フィルターは使わない）。
    """
    safe = image_url.replace("\\", "\\\\").replace('"', '\\"')
    st.markdown(
        f'<link rel="preload" as="image" href="{safe}" />',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <style id="travel-landscape-bg">
            .stApp {{
                position: relative !important;
                isolation: isolate !important;
                background-color: #e8eef5 !important;
                background-image: none !important;
            }}
            .stApp::before {{
                content: "";
                position: fixed;
                inset: 0;
                z-index: -2;
                background-image: url("{safe}");
                background-size: cover;
                background-position: center center;
                background-repeat: no-repeat;
                filter: blur(2px) saturate(1.12) brightness(1.06);
                transform: scale(1.02);
                pointer-events: none;
            }}
            .stApp::after {{
                content: "";
                position: fixed;
                inset: 0;
                z-index: -1;
                pointer-events: none;
                background: linear-gradient(
                    180deg,
                    rgba(255, 255, 255, 0.14) 0%,
                    rgba(255, 255, 255, 0.06) 40%,
                    rgba(15, 23, 42, 0.08) 78%,
                    rgba(15, 23, 42, 0.16) 100%
                );
            }}
            [data-testid="stAppViewContainer"],
            section.main > div {{
                background: transparent !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_styles() -> None:
    """
    全体の見た目（CSS 変数 + セレクタで統一）。
    トーン: 明るく洗練された旅行ブランド（写真主役・ライトガラス・ブルー CTA）。
    """
    st.markdown(
        r"""
        <style>
            @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap");

            :root {
                --t-font: "Inter", -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
                --t-glass: rgba(255, 255, 255, 0.78);
                --t-glass-strong: rgba(255, 255, 255, 0.9);
                --t-glass-border: rgba(15, 23, 42, 0.08);
                --t-glass-inner: rgba(255, 255, 255, 0.95);
                --t-text: #0f172a;
                --t-text-dim: rgba(15, 23, 42, 0.78);
                --t-text-muted: rgba(51, 65, 85, 0.82);
                --t-accent: #0284c7;
                --t-accent-2: #0369a1;
                --t-radius-xl: 24px;
                --t-radius-lg: 18px;
                --t-ease: cubic-bezier(0.16, 1, 0.3, 1);
                --t-cta-from: #38bdf8;
                --t-cta-to: #0284c7;
            }

            @keyframes travel-rise {
                from { opacity: 0; transform: translateY(16px); }
                to { opacity: 1; transform: translateY(0); }
            }

            html { -webkit-text-size-adjust: 100%; }
            html, body, [class*="css"] {
                font-family: var(--t-font) !important;
                -webkit-font-smoothing: antialiased;
            }

            .stApp { background-color: #e8eef5 !important; }
            [data-testid="stHeader"] { background: transparent !important; }

            .stApp, [data-testid="stAppViewContainer"] { overflow-x: hidden; }

            [data-testid="stAppViewContainer"] {
                position: relative;
                z-index: 0;
            }

            /* メインカラム: 中央寄せ・余白 */
            .main { color: var(--t-text); max-width: 100%; }
            .block-container {
                max-width: 820px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding-top: 4.35rem !important;
                padding-bottom: max(4.5rem, env(safe-area-inset-bottom)) !important;
                padding-left: max(1.25rem, env(safe-area-inset-left)) !important;
                padding-right: max(1.25rem, env(safe-area-inset-right)) !important;
            }

            .main .stMarkdown p,
            .main .stMarkdown li,
            .main [data-testid="stCaption"] {
                color: var(--t-text-dim) !important;
            }

            /* ----- Hero（ライトガラス・写真の上でも読みやすく） ----- */
            .travel-hero-shell {
                display: flex;
                justify-content: center;
                padding: 0 0 1.75rem;
            }
            .travel-hero-glass {
                width: 100%;
                max-width: 760px;
                text-align: center;
                padding: clamp(1.75rem, 4.5vw, 2.75rem) clamp(1.25rem, 4vw, 2.5rem);
                border-radius: var(--t-radius-xl);
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(255, 255, 255, 0.65);
                backdrop-filter: blur(12px) saturate(140%);
                -webkit-backdrop-filter: blur(12px) saturate(140%);
                box-shadow:
                    0 4px 6px -1px rgba(15, 23, 42, 0.06),
                    0 24px 48px -12px rgba(15, 23, 42, 0.12),
                    inset 0 1px 0 rgba(255, 255, 255, 0.95);
                animation: travel-rise 0.85s var(--t-ease) both;
            }
            .travel-hero-eyebrow {
                margin: 0 0 0.85rem;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.2em;
                text-transform: uppercase;
                color: var(--t-text-muted);
            }
            .travel-hero-title {
                margin: 0;
                font-size: clamp(2.75rem, 7vw, 4rem);
                font-weight: 800;
                line-height: 1.28;
                letter-spacing: -0.038em;
                color: #0f172a;
                text-wrap: balance;
            }
            .travel-hero-title .travel-hero-accent {
                display: inline;
                color: var(--t-accent);
                font-weight: 800;
            }
            .travel-hero-lead {
                margin: 1.25rem auto 0;
                max-width: 600px;
                font-size: 1.05rem;
                line-height: 1.65;
                font-weight: 400;
                color: rgba(30, 41, 59, 0.82);
            }

            /* ----- メイン中央列のボタン（Hero 下の CTA 用） ----- */
            section.main [data-testid="column"] .stVerticalBlock > div .stButton {
                display: flex;
                justify-content: center;
            }
            section.main [data-testid="column"] .stVerticalBlock > div .stButton > button[kind="secondary"] {
                width: fit-content !important;
                min-width: unset !important;
                padding: 0.65rem 1.35rem !important;
                min-height: 46px !important;
            }

            /* ----- カード外の説明（背景写真の上でも読めるライトガラス帯） ----- */
            .travel-toolbar-caption {
                margin: 0.5rem auto 0;
                max-width: 560px;
                text-align: center;
                color: #1e293b !important;
                font-size: 0.9rem !important;
                line-height: 1.58 !important;
                padding: 0.65rem 1rem;
                border-radius: 14px;
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(255, 255, 255, 0.7);
                box-shadow: 0 2px 12px rgba(15, 23, 42, 0.06);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
            }

            /* ----- 提案カード（白〜半透明ガラス） ----- */
            .card-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 1.35rem;
                width: 100%;
                margin-top: 0.25rem;
            }
            @media (max-width: 960px) {
                .card-grid { grid-template-columns: 1fr; gap: 1.15rem; }
            }

            .travel-card.glass-card {
                border-radius: var(--t-radius-lg);
                overflow: hidden;
                background: rgba(255, 255, 255, 0.8) !important;
                border: 1px solid rgba(255, 255, 255, 0.75) !important;
                backdrop-filter: blur(10px) saturate(135%);
                -webkit-backdrop-filter: blur(10px) saturate(135%);
                box-shadow:
                    0 2px 4px rgba(15, 23, 42, 0.04),
                    0 16px 40px -8px rgba(15, 23, 42, 0.1);
                transition: transform 0.45s var(--t-ease), box-shadow 0.45s var(--t-ease), border-color 0.35s ease;
            }
            @media (hover: hover) and (pointer: fine) {
                .travel-card.glass-card:hover {
                    transform: translateY(-4px);
                    box-shadow:
                        0 8px 16px rgba(15, 23, 42, 0.06),
                        0 28px 48px -12px rgba(15, 23, 42, 0.14);
                    border-color: rgba(255, 255, 255, 0.95) !important;
                }
            }
            .travel-card-top,
            .travel-card-body {
                background: transparent !important;
            }
            .travel-card-top {
                padding: 1.65rem 1.5rem 1.25rem;
                border-bottom: 1px solid rgba(15, 23, 42, 0.06);
            }
            .travel-card-emoji {
                font-size: 2.85rem;
                line-height: 1;
                margin-bottom: 0.85rem;
                filter: drop-shadow(0 2px 8px rgba(15, 23, 42, 0.12));
            }
            .travel-card h3 {
                margin: 0 0 0.55rem;
                font-size: 1.28rem;
                font-weight: 700;
                letter-spacing: -0.02em;
                color: #0f172a;
            }
            .travel-card .tag-pill {
                display: inline-block;
                font-size: 0.74rem;
                font-weight: 600;
                letter-spacing: 0.04em;
                color: var(--t-accent-2);
                background: rgba(2, 132, 199, 0.08);
                border: 1px solid rgba(2, 132, 199, 0.2);
                padding: 0.32rem 0.75rem;
                border-radius: 999px;
            }
            .travel-card-body {
                padding: 1.35rem 1.5rem 1.6rem;
            }
            .travel-card-body p {
                color: rgba(30, 41, 59, 0.88) !important;
            }
            .travel-card-caption {
                margin-top: 1.15rem;
                padding-top: 1.1rem;
                border-top: 1px solid rgba(15, 23, 42, 0.06);
                font-size: 0.78rem;
                line-height: 1.5;
                color: rgba(71, 85, 105, 0.95) !important;
            }

            .travel-card-story .travel-pitch-reason {
                margin: 0 0 1rem;
                font-size: 1.03rem;
                line-height: 1.72;
                color: #0f172a !important;
                font-weight: 600;
            }
            .travel-card-story .travel-pitch-lead {
                margin: 0 0 1rem;
                font-size: 0.98rem;
                line-height: 1.65;
                color: rgba(30, 41, 59, 0.85) !important;
            }
            .travel-pitch-block { margin-top: 1.05rem; }
            .travel-pitch-label {
                display: block;
                margin-bottom: 0.45rem;
                font-size: 0.66rem;
                font-weight: 700;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                color: var(--t-accent);
            }
            .travel-pitch-block p:not(.travel-pitch-reason) {
                margin: 0 !important;
                font-size: 0.92rem !important;
                line-height: 1.65 !important;
                color: rgba(30, 41, 59, 0.86) !important;
            }

            /* ----- Streamlit ボタン ----- */
            .stButton > button {
                border-radius: 999px !important;
                font-weight: 600 !important;
                font-size: 0.98rem !important;
                letter-spacing: -0.01em !important;
                transition:
                    transform 0.35s var(--t-ease),
                    box-shadow 0.35s var(--t-ease),
                    background 0.25s ease,
                    border-color 0.25s ease !important;
            }

            /* メイン primary = 上品なブルー CTA（Streamlit デフォルトの赤を上書き） */
            section.main button[kind="primary"] {
                width: fit-content !important;
                min-width: 12rem !important;
                padding: 0.85rem 2.15rem !important;
                min-height: 52px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                display: block !important;
                background: linear-gradient(165deg, var(--t-cta-from) 0%, #0ea5e9 45%, var(--t-cta-to) 100%) !important;
                color: #ffffff !important;
                border: 1px solid rgba(255, 255, 255, 0.35) !important;
                box-shadow:
                    0 4px 14px rgba(2, 132, 199, 0.35),
                    inset 0 1px 0 rgba(255, 255, 255, 0.35) !important;
            }
            @media (hover: hover) and (pointer: fine) {
                section.main button[kind="primary"]:hover {
                    transform: translateY(-3px);
                    box-shadow:
                        0 12px 28px rgba(2, 132, 199, 0.4),
                        inset 0 1px 0 rgba(255, 255, 255, 0.45) !important;
                }
            }

            /* secondary = ライトガラス（カードと統一） */
            section.main button[kind="secondary"] {
                background: rgba(255, 255, 255, 0.78) !important;
                color: #1e293b !important;
                border: 1px solid rgba(255, 255, 255, 0.85) !important;
                backdrop-filter: blur(8px);
                -webkit-backdrop-filter: blur(8px);
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06) !important;
            }
            @media (hover: hover) and (pointer: fine) 
                section.main button[kind="secondary"]:hover {
                    background: rgba(255, 255, 255, 0.95) !important;
                    border-color: rgba(255, 255, 255, 1) !important;
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.1) !important;
                }
            }

            /* サイドバー内 primary: 同じブルー CTA・全幅 */
            section[data-testid="stSidebar"] button[kind="primary"] {
                width: 100% !important;
                margin-left: 0 !important;
                margin-right: 0 !important;
                background: linear-gradient(165deg, var(--t-cta-from) 0%, #0ea5e9 45%, var(--t-cta-to) 100%) !important;
                color: #ffffff !important;
                border: 1px solid rgba(255, 255, 255, 0.35) !important;
                box-shadow: 0 4px 14px rgba(2, 132, 199, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
            }
            @media (hover: hover) and (pointer: fine) {
                section[data-testid="stSidebar"] button[kind="primary"]:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 10px 24px rgba(2, 132, 199, 0.38) !important;
                }
            }

            /* ----- 左上メニュー: 46px 角丸正方形・ライトガラス ----- */
            section.main .block-container div[data-testid="stVerticalBlock"] > div:first-child button[kind="secondary"] {
                position: fixed !important;
                left: max(16px, env(safe-area-inset-left)) !important;
                top: max(14px, env(safe-area-inset-top)) !important;
                width: 46px !important;
                height: 46px !important;
                min-height: 46px !important;
                min-width: 46px !important;
                padding: 0 !important;
                margin: 0 !important;
                border-radius: 14px !important;
                z-index: 100050 !important;
                font-size: 1.35rem !important;
                font-weight: 800 !important;
                line-height: 1 !important;
                letter-spacing: 0 !important;
                background: rgba(255, 255, 255, 0.82) !important;
                color: #0f172a !important;
                border: 1px solid rgba(255, 255, 255, 0.9) !important;
                backdrop-filter: blur(10px) saturate(140%) !important;
                -webkit-backdrop-filter: blur(10px) saturate(140%) !important;
                box-shadow:
                    0 2px 6px rgba(15, 23, 42, 0.08),
                    0 12px 28px rgba(15, 23, 42, 0.12),
                    inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
            }
            @media (hover: hover) and (pointer: fine) {
                section.main .block-container div[data-testid="stVerticalBlock"] > div:first-child button[kind="secondary"]:hover {
                    transform: translateY(-2px);
                    background: rgba(255, 255, 255, 0.95) !important;
                    box-shadow:
                        0 6px 16px rgba(15, 23, 42, 0.12),
                        0 18px 36px rgba(15, 23, 42, 0.14) !important;
                }
            }

            /* ----- ドロワー用スクリム（軽め） ----- */
            .travel-drawer-scrim {
                position: fixed;
                inset: 0;
                z-index: 100040;
                background: rgba(15, 23, 42, 0.22);
                backdrop-filter: blur(6px);
                -webkit-backdrop-filter: blur(6px);
                pointer-events: auto;
            }

            /* ----- サイドバー（明るいガラスパネル） ----- */
            section[data-testid="stSidebar"] {
                background: rgba(255, 255, 255, 0.88) !important;
                backdrop-filter: blur(16px) saturate(130%) !important;
                -webkit-backdrop-filter: blur(16px) saturate(130%) !important;
                border-right: 1px solid rgba(15, 23, 42, 0.06) !important;
                box-shadow: 8px 0 40px rgba(15, 23, 42, 0.08) !important;
            }
            [data-testid="stSidebar"] .stMarkdown h3 { color: #0f172a !important; }
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
                color: #0f172a !important;
            }
            [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
                color: rgba(30, 41, 59, 0.78) !important;
            }
            [data-testid="stSidebar"] hr {
                border-color: rgba(15, 23, 42, 0.08) !important;
            }
            [data-testid="stSidebar"] input,
            [data-testid="stSidebar"] [role="slider"] {
                accent-color: var(--t-accent);
            }
            [data-testid="stSidebar"] button[kind="secondary"] {
                background: rgba(248, 250, 252, 0.95) !important;
                color: #334155 !important;
                border: 1px solid rgba(15, 23, 42, 0.1) !important;
            }
            [data-testid="stSidebar"] textarea,
            [data-testid="stSidebar"] [data-baseweb="textarea"] textarea {
                background-color: #ffffff !important;
                color: #0f172a !important;
                border-color: rgba(148, 163, 184, 0.5) !important;
                caret-color: var(--t-accent) !important;
            }
            [data-testid="stSidebar"] [data-baseweb="select"] > div,
            [data-testid="stSidebar"] [data-baseweb="input"] input {
                background-color: #ffffff !important;
                color: #0f172a !important;
            }

            /* サイドバー primary: 下端 Sticky で長いパネルでも常にタップ可能（特にスマホ） */
            section[data-testid="stSidebar"] div[data-testid="element-container"]:has(button[kind="primary"]) {
                position: sticky !important;
                bottom: max(10px, env(safe-area-inset-bottom)) !important;
                z-index: 60 !important;
                margin-top: 0.5rem !important;
                padding-top: 0.65rem !important;
                padding-bottom: max(4px, env(safe-area-inset-bottom)) !important;
                background: linear-gradient(
                    to top,
                    rgba(255, 255, 255, 0.98) 40%,
                    rgba(255, 255, 255, 0.92) 100%
                ) !important;
                backdrop-filter: blur(10px) !important;
                -webkit-backdrop-filter: blur(10px) !important;
                border-radius: 14px !important;
                box-shadow: 0 -6px 20px rgba(15, 23, 42, 0.06) !important;
            }

            /* Alerts / info（ライト UI 向け） */
            [data-testid="stSuccess"] {
                background: rgba(220, 252, 231, 0.92) !important;
                border: 1px solid rgba(34, 197, 94, 0.35) !important;
                border-radius: 16px !important;
                backdrop-filter: blur(8px);
            }
            [data-testid="stSuccess"] * { color: #14532d !important; }
            [data-testid="stAlert"] {
                background: rgba(255, 255, 255, 0.88) !important;
                border: 1px solid rgba(15, 23, 42, 0.08) !important;
                border-radius: 16px !important;
                backdrop-filter: blur(8px);
            }
            [data-testid="stAlert"] * {
                color: #334155 !important;
            }
            [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p,
            [data-testid="stAlert"] p {
                color: #1e293b !important;
            }

            [data-testid="collapsedControl"] { display: none !important; }

            @media (max-width: 640px) {
                .block-container { padding-top: 5rem !important; }
                .travel-hero-glass { padding: 1.75rem 1.2rem; border-radius: 22px; }
                .travel-hero-title { font-size: clamp(2.1rem, 9vw, 2.75rem); }
            }
            @media (max-width: 480px) {
                .travel-hero-title br { display: none; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_drawer_styles(menu_open: bool) -> None:
    """サイドバーを左からスライドするドロワーとして扱う（開閉は session_state.menu_open）。"""
    tx = "0%" if menu_open else "-100%"
    # 閉じているときはクリックを受け付けない（translate で見えなくても背面でヒット領域が残るのを防ぐ）
    ptr = "auto" if menu_open else "none"
    st.markdown(
        f"""
        <style id="travel-drawer-dynamic">
            section[data-testid="stSidebar"] {{
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                bottom: 0 !important;
                height: 100vh !important;
                height: 100dvh !important;
                width: min(88vw, 390px) !important;
                min-width: 260px !important;
                max-width: 100% !important;
                transform: translateX({tx}) !important;
                transition: transform 0.2s cubic-bezier(0.22, 1, 0.36, 1) !important;
                will-change: transform;
                pointer-events: {ptr} !important;
                z-index: 100045 !important;
                border-radius: 0 22px 22px 0 !important;
                overflow-x: hidden !important;
                overflow-y: auto !important;
                -webkit-overflow-scrolling: touch !important;
                box-shadow: 8px 0 36px rgba(15, 23, 42, 0.12) !important;
                margin-left: 0 !important;
            }}
            section[data-testid="stSidebar"] > div {{
                width: 100% !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _on_drawer_toggle() -> None:
    st.session_state.menu_open = not st.session_state.menu_open


def _on_drawer_close() -> None:
    st.session_state.menu_open = False


def _on_refresh_wallpaper() -> None:
    st.session_state.wallpaper_seed = random.randint(1, 999_999_999)
    st.session_state.pop("wallpaper_url", None)


def _on_sidebar_request_ai_proposal() -> None:
    """
    サイドバー下の「AIに提案」から呼ばれる。
    ドロワーを閉じたあと、メイン側で API 実行するためフラグを立てる。
    """
    st.session_state.menu_open = False
    st.session_state.pending_proposal = True


def _render_travel_proposals(
    theme_text: str,
    budget_man: int,
    trip_days: int,
    season: str,
) -> None:
    """OpenAI 取得〜カード表示まで（メイン／サイドバーどちらのボタンからも同じ処理）。"""
    with st.spinner("OpenAI が条件に合う旅先を考えています…（30秒ほどかかることもあります）"):
        suggestions, err = fetch_travel_suggestions_openai(
            theme_text, budget_man, trip_days, season
        )

    if err:
        st.warning("API から取得できなかったため、セットアップ用のカードを表示しています。")
        suggestions = fallback_demo_cards(
            theme_text, budget_man, trip_days, season, err
        )
    else:
        st.success("OpenAI から3件の提案を受け取りました。")

    def esc(s: str) -> str:
        return (
            (s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    cards_html = ['<div class="card-grid">']
    for item in suggestions:
        name = esc(item["name"])
        tag = esc(item["tag"])
        cap = esc(item.get("subtitle", ""))
        emoji = esc(item.get("emoji", "✈️"))
        reason = esc(item.get("pitch_reason", ""))
        desc = esc(item.get("pitch_lead", ""))
        atm = esc(item.get("pitch_atmosphere", ""))
        whom = esc(item.get("pitch_for_who", ""))
        xp = esc(item.get("pitch_experiences", ""))
        price = esc(item.get("price_estimate", ""))
        reason_html = ""
        if reason:
            reason_html = (
                f'<div class="travel-pitch-block">'
                f'<span class="travel-pitch-label">おすすめ理由</span>'
                f'<p class="travel-pitch-reason">{reason}</p>'
                f"</div>"
            )
        desc_html = ""
        if desc:
            desc_html = (
                f'<div class="travel-pitch-block">'
                f'<span class="travel-pitch-label">どんなところか</span>'
                f"<p>{desc}</p>"
                f"</div>"
            )
        cards_html.append(
            f'<div class="travel-card glass-card">'
            f'<div class="travel-card-top">'
            f'<div class="travel-card-emoji">{emoji}</div>'
            f"<h3>{name}</h3>"
            f'<span class="tag-pill">{tag}</span>'
            f"</div>"
            f'<div class="travel-card-body travel-card-story">'
            f"{reason_html}"
            f"{desc_html}"
            f'<div class="travel-pitch-block">'
            f'<span class="travel-pitch-label">空気感</span>'
            f"<p>{atm}</p>"
            f"</div>"
            f'<div class="travel-pitch-block">'
            f'<span class="travel-pitch-label">こんな人におすすめ</span>'
            f"<p>{whom}</p>"
            f"</div>"
            f'<div class="travel-pitch-block">'
            f'<span class="travel-pitch-label">体験のヒント</span>'
            f"<p>{xp}</p>"
            f"</div>"
            f'<div class="travel-pitch-block">'
            f'<span class="travel-pitch-label">料金の目安</span>'
            f"<p>{price}</p>"
            f"</div>"
            f'<p class="travel-card-caption">{cap}</p>'
            f"</div></div>"
        )
    cards_html.append("</div>")
    st.markdown("".join(cards_html), unsafe_allow_html=True)

    st.info(
        "モデルは `gpt-4o-mini`、応答は **JSON モード**（`response_format`）です。"
        "各旅先の **reason** が「おすすめ理由」として表示されます。"
        "プロンプトを変えるときは `fetch_travel_suggestions_openai` 内の文言と `_JSON_SHAPE_USER_HINT` を揃えてください。"
    )


def main() -> None:
    st.set_page_config(
        page_title="Travel AI — 次の旅をデザインする",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "menu_open" not in st.session_state:
        st.session_state.menu_open = False
    # サイドバー下のボタンから API を走らせるとき True（1回きり消費）
    if "pending_proposal" not in st.session_state:
        st.session_state.pending_proposal = False

    inject_styles()
    inject_landscape_background(_session_landscape_wallpaper_url())
    inject_drawer_styles(st.session_state.menu_open)

    # kind=secondary のボタンだけを CSS で左上 FAB にしているため type を明示
    # （スクリムより先に置き、常にメイン縦ブロックの先頭＝FAB 用セレクタと一致させる）
    st.button(
        "☰",
        key="travel_menu_toggle",
        type="secondary",
        help="旅の条件パネルを開く／閉じる",
        on_click=_on_drawer_toggle,
    )

    if st.session_state.menu_open:
        st.markdown(
            '<div class="travel-drawer-scrim" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="travel-hero-shell">
          <div class="travel-hero-glass">
            <p class="travel-hero-eyebrow">Travel AI</p>
            <h1 class="travel-hero-title">
              条件を整えたら、<br />
              <span class="travel-hero-accent">次の旅先</span>が浮かび上がる。
            </h1>
            <p class="travel-hero-lead">
              テーマ・予算・日数・季節を決めるだけ。OpenAI が JSON で3件の候補を返し、
              すぐにカードで比較して次の旅を選べます。
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        head_l, head_r = st.columns([5, 1])
        with head_l:
            st.markdown("### 旅の条件")
        with head_r:
            st.button(
                "✕",
                key="travel_drawer_close",
                help="パネルを閉じる",
                on_click=_on_drawer_close,
            )

        # 旅行テーマは「自由記述」。複数行書ける text_area を使う（height で高さ指定）
        theme_text = st.text_area(
            "旅行テーマ（自由入力）",
            value="温泉でまったり、夜景も楽しみたい",
            height=96,
            help="例: グルメ中心の台湾、絶景ハイキング、家族で沖縄… 好きな言葉でOKです。",
        )

        # 予算は万円単位のスライダー（航空券は含めない前提でプロンプト側に明記済み）
        budget_man = st.slider(
            "予算の目安（万円）",
            min_value=3,
            max_value=80,
            value=12,
            step=1,
            help="現地での宿・食・国内交通・体験などのざっくり目安（航空券は別途イメージ）。",
        )

        trip_days = st.slider(
            "旅行日数（往復入り・全日程）",
            min_value=1,
            max_value=14,
            value=3,
        )

        # 春〜冬の4択（要件どおり。Streamlit の selectbox でシンプルに）
        season = st.selectbox(
            "いつ頃行きたいか",
            options=["春", "夏", "秋", "冬"],
            index=0,
        )

        # スマホでもスクロールせず押しやすいよう、条件入力の直後に CTA を置く
        # （押すとドロワーが閉じ、メインで AI 提案が走る pending_proposal）
        st.button(
            "この条件で AI に提案してもらう",
            type="primary",
            use_container_width=True,
            key="sidebar_ai_propose",
            help="提案を開始し、このパネルを閉じます",
            on_click=_on_sidebar_request_ai_proposal,
        )

        st.divider()
        st.caption(
            "API キーは `.env` に `OPENAI_API_KEY=` を記述。"
            "初めての方はリポジトリの `.env.example` をコピーしてファイル名を `.env` にしてください。"
        )

    # -------------------------------------------------------------------------
    # メイン処理: メインのボタン OR サイドバーからの pending で OpenAI → カード
    # -------------------------------------------------------------------------
    from_sidebar = st.session_state.pop("pending_proposal", False)

    _, cta_mid, _ = st.columns([1, 3, 1])
    with cta_mid:
        main_clicked = st.button(
            "この条件で AI に提案してもらう",
            type="primary",
            use_container_width=False,
            key="main_ai_propose",
            help="現在のサイドバー条件で提案を取得します",
        )
        st.markdown(
            '<div style="height:0.65rem" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        st.button(
            "別の風景にする",
            key="refresh_wallpaper",
            type="secondary",
            help="ランダムな別画像に切り替え（高速 CDN）",
            use_container_width=False,
            on_click=_on_refresh_wallpaper,
        )
        st.markdown(
            '<p class="travel-toolbar-caption">'
            "背景は <strong>Picsum Photos</strong> のフリー写真です。"
            "風景はいつでも差し替えられます。</p>",
            unsafe_allow_html=True,
        )
        if not (main_clicked or from_sidebar):
            st.markdown(
                '<p class="travel-toolbar-caption" style="margin-top:1.5rem">'
                "左上の <strong>☰</strong> で条件パネルを開き、"
                "テーマ・予算・日数・季節を入力してから、上のボタンで提案を開始してください。</p>",
                unsafe_allow_html=True,
            )

    if main_clicked or from_sidebar:
        _render_travel_proposals(theme_text, budget_man, trip_days, season)


if __name__ == "__main__":
    main()

