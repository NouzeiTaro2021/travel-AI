# ワンショット: inject_styles() の中身を全面差し替え（実行後このファイルは削除可）
from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / "travel_ai.py"
text = path.read_text(encoding="utf-8")
start = text.find("def inject_styles() -> None:")
end = text.find("def inject_drawer_styles(menu_open: bool) -> None:")
if start == -1 or end == -1 or end <= start:
    raise SystemExit("markers not found")

NEW = r'''def inject_styles() -> None:
    """
    全体の見た目（Tailwind のビルドは使えないため、CSS 変数 + ユーティリティ風セレクタで再現）。
    トーン: 静かな高級感 / 深夜ラウンジ / ガラス（glassmorphism）。
    """
    st.markdown(
        r"""
        <style>
            @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");

            :root {
                --t-font: "Inter", -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
                --t-glass: rgba(255, 255, 255, 0.072);
                --t-glass-strong: rgba(255, 255, 255, 0.1);
                --t-glass-border: rgba(255, 255, 255, 0.14);
                --t-glass-inner: rgba(255, 255, 255, 0.2);
                --t-text: rgba(255, 255, 255, 0.96);
                --t-text-dim: rgba(255, 255, 255, 0.75);
                --t-text-muted: rgba(255, 255, 255, 0.52);
                --t-accent: #a5d8ff;
                --t-accent-2: #7dd3fc;
                --t-radius-xl: 28px;
                --t-radius-lg: 20px;
                --t-ease: cubic-bezier(0.16, 1, 0.3, 1);
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

            .stApp { background-color: #06080d !important; }
            [data-testid="stHeader"] { background: transparent !important; }

            .stApp, [data-testid="stAppViewContainer"] { overflow-x: hidden; }

            [data-testid="stAppViewContainer"] {
                position: relative;
                z-index: 0;
            }

            /* メインカラム: 中央寄せ・余白（720〜840px 相当） */
            .main { color: var(--t-text); max-width: 100%; }
            .block-container {
                max-width: 820px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding-top: 5.75rem !important;
                padding-bottom: max(4.5rem, env(safe-area-inset-bottom)) !important;
                padding-left: max(1.25rem, env(safe-area-inset-left)) !important;
                padding-right: max(1.25rem, env(safe-area-inset-right)) !important;
            }

            .main .stMarkdown p,
            .main .stMarkdown li,
            .main [data-testid="stCaption"] {
                color: var(--t-text-dim) !important;
            }

            /* ----- Hero（中央・ガラス・没入感） ----- */
            .travel-hero-shell {
                display: flex;
                justify-content: center;
                padding: 0.5rem 0 2.25rem;
            }
            .travel-hero-glass {
                width: 100%;
                max-width: 760px;
                text-align: center;
                padding: clamp(2rem, 5vw, 3.25rem) clamp(1.25rem, 4vw, 2.75rem);
                border-radius: var(--t-radius-xl);
                background: var(--t-glass);
                border: 1px solid var(--t-glass-border);
                backdrop-filter: blur(28px) saturate(165%);
                -webkit-backdrop-filter: blur(28px) saturate(165%);
                box-shadow:
                    0 28px 90px rgba(0, 0, 0, 0.28),
                    inset 0 1px 0 var(--t-glass-inner);
                animation: travel-rise 0.85s var(--t-ease) both;
            }
            .travel-hero-eyebrow {
                margin: 0 0 1rem;
                font-size: 0.72rem;
                font-weight: 600;
                letter-spacing: 0.22em;
                text-transform: uppercase;
                color: var(--t-text-muted);
            }
            .travel-hero-title {
                margin: 0;
                font-size: clamp(2.75rem, 7vw, 4rem);
                font-weight: 700;
                line-height: 1.18;
                letter-spacing: -0.035em;
                color: var(--t-text);
                text-wrap: balance;
            }
            .travel-hero-title .travel-hero-accent {
                display: inline;
                color: var(--t-accent-2);
                font-weight: 700;
            }
            .travel-hero-lead {
                margin: 1.35rem auto 0;
                max-width: 600px;
                font-size: 1.08rem;
                line-height: 1.68;
                font-weight: 400;
                color: var(--t-text-dim);
                opacity: 0.95;
            }

            /* ----- ツールバー（キャプション + secondary） ----- */
            .travel-toolbar-caption {
                color: var(--t-text-muted) !important;
                font-size: 0.88rem !important;
            }

            /* ----- ガラスカード（ベタ黒禁止） ----- */
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
                background: var(--t-glass) !important;
                border: 1px solid var(--t-glass-border) !important;
                backdrop-filter: blur(22px) saturate(150%);
                -webkit-backdrop-filter: blur(22px) saturate(150%);
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.22);
                transition: transform 0.45s var(--t-ease), box-shadow 0.45s var(--t-ease), border-color 0.35s ease;
            }
            @media (hover: hover) and (pointer: fine) {
                .travel-card.glass-card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 28px 70px rgba(0, 0, 0, 0.32);
                    border-color: rgba(255, 255, 255, 0.22) !important;
                }
            }
            .travel-card-top,
            .travel-card-body {
                background: transparent !important;
            }
            .travel-card-top {
                padding: 1.65rem 1.5rem 1.25rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            .travel-card-emoji {
                font-size: 2.85rem;
                line-height: 1;
                margin-bottom: 0.85rem;
                filter: drop-shadow(0 6px 18px rgba(0, 0, 0, 0.35));
            }
            .travel-card h3 {
                margin: 0 0 0.55rem;
                font-size: 1.28rem;
                font-weight: 600;
                letter-spacing: -0.02em;
                color: var(--t-text);
            }
            .travel-card .tag-pill {
                display: inline-block;
                font-size: 0.74rem;
                font-weight: 600;
                letter-spacing: 0.04em;
                color: var(--t-accent);
                background: rgba(165, 216, 255, 0.12);
                border: 1px solid rgba(165, 216, 255, 0.22);
                padding: 0.32rem 0.75rem;
                border-radius: 999px;
            }
            .travel-card-body {
                padding: 1.35rem 1.5rem 1.6rem;
            }
            .travel-card-body p {
                color: var(--t-text-dim) !important;
            }
            .travel-card-caption {
                margin-top: 1.15rem;
                padding-top: 1.1rem;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                font-size: 0.78rem;
                line-height: 1.5;
                color: var(--t-text-muted) !important;
            }

            .travel-card-story .travel-pitch-reason {
                margin: 0 0 1rem;
                font-size: 1.03rem;
                line-height: 1.72;
                color: var(--t-text) !important;
                font-weight: 500;
            }
            .travel-card-story .travel-pitch-lead {
                margin: 0 0 1rem;
                font-size: 0.98rem;
                line-height: 1.65;
                color: var(--t-text-dim) !important;
            }
            .travel-pitch-block { margin-top: 1.05rem; }
            .travel-pitch-label {
                display: block;
                margin-bottom: 0.45rem;
                font-size: 0.66rem;
                font-weight: 700;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                color: var(--t-accent-2);
            }
            .travel-pitch-block p:not(.travel-pitch-reason) {
                margin: 0 !important;
                font-size: 0.92rem !important;
                line-height: 1.65 !important;
                color: var(--t-text-dim) !important;
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

            /* メインエリアの primary = CTA（横幅は内容に合わせて中央） */
            section.main button[kind="primary"] {
                width: fit-content !important;
                min-width: 12rem !important;
                padding: 0.85rem 2.15rem !important;
                min-height: 52px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                display: block !important;
                background: linear-gradient(135deg, #f0f7ff 0%, #d4e9ff 38%, #b8dcff 100%) !important;
                color: #0a1624 !important;
                border: 1px solid rgba(255, 255, 255, 0.55) !important;
                box-shadow:
                    0 14px 40px rgba(125, 211, 252, 0.18),
                    inset 0 1px 0 rgba(255, 255, 255, 0.75) !important;
            }
            @media (hover: hover) and (pointer: fine) {
                section.main button[kind="primary"]:hover {
                    transform: translateY(-2px) scale(1.02);
                    box-shadow:
                        0 22px 50px rgba(125, 211, 252, 0.28),
                        inset 0 1px 0 rgba(255, 255, 255, 0.85) !important;
                }
            }

            /* secondary = ガラス（別の風景・メニュー FAB 以外にも効くが、下で FAB を上書き） */
            section.main button[kind="secondary"] {
                background: rgba(255, 255, 255, 0.08) !important;
                color: var(--t-text) !important;
                border: 1px solid var(--t-glass-border) !important;
                backdrop-filter: blur(14px);
                -webkit-backdrop-filter: blur(14px);
            }
            @media (hover: hover) and (pointer: fine) {
                section.main button[kind="secondary"]:hover {
                    background: rgba(255, 255, 255, 0.14) !important;
                    border-color: rgba(255, 255, 255, 0.24) !important;
                    transform: translateY(-1px);
                }
            }

            /* サイドバー内 primary は全幅のまま */
            section[data-testid="stSidebar"] button[kind="primary"] {
                width: 100% !important;
                margin-left: 0 !important;
                margin-right: 0 !important;
            }

            /* ----- 左上メニュー FAB: 1.5倍 + glass + z-index ----- */
            section.main .block-container div[data-testid="stVerticalBlock"] > div:first-child button[kind="secondary"] {
                position: fixed !important;
                left: max(18px, env(safe-area-inset-left)) !important;
                top: max(18px, env(safe-area-inset-top)) !important;
                width: 72px !important;
                height: 72px !important;
                min-height: 72px !important;
                padding: 0 !important;
                margin: 0 !important;
                border-radius: 50% !important;
                z-index: 100050 !important;
                font-size: 1.65rem !important;
                line-height: 1 !important;
                background: rgba(255, 255, 255, 0.1) !important;
                border: 1px solid rgba(255, 255, 255, 0.22) !important;
                backdrop-filter: blur(22px) saturate(160%) !important;
                -webkit-backdrop-filter: blur(22px) saturate(160%) !important;
                box-shadow:
                    0 12px 40px rgba(0, 0, 0, 0.35),
                    inset 0 1px 0 rgba(255, 255, 255, 0.28) !important;
            }
            @media (hover: hover) and (pointer: fine) {
                section.main .block-container div[data-testid="stVerticalBlock"] > div:first-child button[kind="secondary"]:hover {
                    transform: scale(1.05) translateY(-1px);
                    background: rgba(255, 255, 255, 0.16) !important;
                }
            }

            /* ----- ドロワー用スクリム（FABより下） ----- */
            .travel-drawer-scrim {
                position: fixed;
                inset: 0;
                z-index: 100040;
                background: rgba(4, 6, 12, 0.45);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                pointer-events: auto;
            }

            /* ----- サイドバー（ガラス） ----- */
            section[data-testid="stSidebar"] {
                background: rgba(255, 255, 255, 0.06) !important;
                backdrop-filter: blur(32px) saturate(160%) !important;
                -webkit-backdrop-filter: blur(32px) saturate(160%) !important;
                border-right: 1px solid var(--t-glass-border) !important;
            }
            [data-testid="stSidebar"] .stMarkdown h3 { color: var(--t-text) !important; }
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
                color: var(--t-text) !important;
            }
            [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
                color: var(--t-text-dim) !important;
            }
            [data-testid="stSidebar"] hr {
                border-color: rgba(255, 255, 255, 0.1) !important;
            }
            [data-testid="stSidebar"] input,
            [data-testid="stSidebar"] [role="slider"] {
                accent-color: var(--t-accent-2);
            }

            /* Alerts / info をガラス寄せ */
            [data-testid="stSuccess"] {
                background: rgba(52, 199, 89, 0.12) !important;
                border: 1px solid rgba(52, 199, 89, 0.35) !important;
                border-radius: 16px !important;
                backdrop-filter: blur(12px);
            }
            [data-testid="stSuccess"] * { color: rgba(230, 250, 235, 0.95) !important; }
            [data-testid="stAlert"] {
                background: rgba(255, 255, 255, 0.06) !important;
                border: 1px solid var(--t-glass-border) !important;
                border-radius: 16px !important;
                backdrop-filter: blur(14px);
            }
            [data-testid="stAlert"] * {
                color: var(--t-text-dim) !important;
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


'''

path.write_text(text[:start] + NEW + text[end:], encoding="utf-8")
print("OK")
