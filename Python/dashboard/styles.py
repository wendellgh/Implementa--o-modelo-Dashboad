import streamlit as st

TEMA_VISUAL_KEY = "tema_visual"
TEMA_CLARO_ATIVO_KEY = "tema_claro_ativo"
TEMA_ESCURO = "Escuro"
TEMA_CLARO = "Claro"
TEMAS_DISPONIVEIS = (TEMA_ESCURO, TEMA_CLARO)


def obter_tema_visual() -> str:
    return TEMA_CLARO if tema_claro_ativo() else TEMA_ESCURO


def tema_claro_ativo() -> bool:
    tema_toggle = st.session_state.get(TEMA_CLARO_ATIVO_KEY)
    if isinstance(tema_toggle, bool):
        return tema_toggle

    tema_antigo = str(st.session_state.get(TEMA_VISUAL_KEY, TEMA_ESCURO))
    if tema_antigo in TEMAS_DISPONIVEIS:
        return tema_antigo == TEMA_CLARO

    return False


def _tokens_tema_css() -> str:
    if tema_claro_ativo():
        return """
            :root,
            .stApp {
                --tacom-page-background: linear-gradient(135deg, #f7f9fc 0%, #eef4fb 100%);
                --tacom-bg: #f7f9fc;
                --tacom-bg-soft: #eef3f8;
                --tacom-sidebar: #ffffff;
                --tacom-panel: #ffffff;
                --tacom-panel-strong: #f8fbff;
                --tacom-panel-hover: #edf4ff;
                --tacom-input-bg: #ffffff;
                --tacom-border: rgba(37, 56, 78, 0.18);
                --tacom-border-strong: rgba(20, 120, 255, 0.38);
                --tacom-primary: #1478ff;
                --tacom-primary-strong: #0b5ed7;
                --tacom-secondary: #087f95;
                --tacom-success: #17803d;
                --tacom-warning: #a16207;
                --tacom-accent: #d92d20;
                --tacom-red: #d92d20;
                --tacom-red-dark: #9f1712;
                --tacom-red-light: #ef6f68;
                --tacom-text: #1f2937;
                --tacom-muted: #526071;
                --tacom-muted-2: #7b8794;
                --tacom-shadow: 0 18px 50px rgba(17, 24, 39, 0.08);
                --tacom-glow: 0 0 0 1px rgba(20, 120, 255, 0.10),
                    0 18px 40px rgba(17, 24, 39, 0.08);
            }
        """

    return """
            :root,
            .stApp {
                --tacom-page-background: linear-gradient(135deg, #050b14 0%, #06111e 48%, #03101d 100%);
                --tacom-bg: #050b14;
                --tacom-bg-soft: #071321;
                --tacom-sidebar: #040914;
                --tacom-panel: #0a1727;
                --tacom-panel-strong: #0d1f34;
                --tacom-panel-hover: #102842;
                --tacom-input-bg: #071321;
                --tacom-border: rgba(118, 150, 190, 0.22);
                --tacom-border-strong: rgba(0, 180, 255, 0.38);
                --tacom-primary: #1478ff;
                --tacom-primary-strong: #0b5ed7;
                --tacom-secondary: #20d0e8;
                --tacom-success: #22c55e;
                --tacom-warning: #f59e0b;
                --tacom-accent: #ff3b30;
                --tacom-red: #ff3b30;
                --tacom-red-dark: #9f1712;
                --tacom-red-light: #ff7a70;
                --tacom-text: #f4f8ff;
                --tacom-muted: #9aa9bd;
                --tacom-muted-2: #66758a;
                --tacom-shadow: 0 18px 50px rgba(0, 0, 0, 0.34);
                --tacom-glow: 0 0 0 1px rgba(0, 180, 255, 0.12),
                    0 18px 40px rgba(0, 0, 0, 0.28);
            }
        """


def aplicar_estilos_globais() -> None:
    st.markdown(
        """
        <style>
        """
        + _tokens_tema_css()
        + """
            .stApp,
            div[data-testid="stAppViewContainer"] {
                background: var(--tacom-page-background) !important;
                background-attachment: fixed !important;
                color: var(--tacom-text);
            }

            .stApp {
                font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
            }

            .stApp * {
                letter-spacing: 0;
            }

            .stMain,
            section[data-testid="stAppScrollToBottomContainer"] {
                background: transparent !important;
            }

            header[data-testid="stHeader"] {
                background: color-mix(in srgb, var(--tacom-bg) 86%, transparent);
                border-bottom: 1px solid var(--tacom-border);
                box-shadow: none;
                backdrop-filter: blur(14px);
            }

            div[data-testid="stDecoration"],
            div[data-testid="stLogoSpacer"] {
                display: none;
            }

            .block-container {
                max-width: 100%;
                padding: 2.15rem 2rem 1.25rem 2rem;
            }

            h1, h2, h3, h4, h5, h6,
            p, label, span, div[data-testid="stMarkdownContainer"] {
                color: var(--tacom-text);
            }

            div[data-testid="stMarkdownContainer"] p,
            div[data-testid="stCaptionContainer"],
            small {
                color: var(--tacom-muted);
            }

            .main-title {
                margin: 0.65rem 0 1.25rem 0;
                padding: 0.1rem 0 0.2rem 0;
                color: var(--tacom-text);
                font-size: clamp(1.45rem, 1.8vw, 2rem);
                font-weight: 760;
                line-height: 1.25;
                overflow-wrap: anywhere;
            }

            .filters-title {
                margin: 0.15rem 0 0.8rem 0;
                color: var(--tacom-text);
                font-size: 0.86rem;
                font-weight: 760;
                text-transform: uppercase;
            }

            section[data-testid="stSidebar"] {
                background:
                    linear-gradient(180deg, var(--tacom-sidebar) 0%, var(--tacom-bg-soft) 100%);
                border-right: 1px solid var(--tacom-border);
                box-shadow: 18px 0 38px rgba(0, 0, 0, 0.18);
            }

            div[data-testid="stSidebarContent"] {
                padding: 1rem 1rem 1.35rem 1rem;
            }

            div[data-testid="stSidebarHeader"] {
                height: 2rem !important;
                min-height: 0 !important;
                width: 2rem !important;
                margin: 0 !important;
                padding: 0 !important;
                position: absolute !important;
                top: 0.5rem;
                right: 0.5rem;
                z-index: 3;
            }

            div[data-testid="stSidebarUserContent"] {
                padding-top: 0 !important;
            }

            div[data-testid="stMarkdownContainer"]:has(.sidebar-logo) {
                margin-bottom: 0 !important;
            }

            .sidebar-logo {
                margin: 0 0 1rem 0;
                padding: 0.15rem 0 0.9rem 0;
                border-bottom: 1px solid var(--tacom-border);
            }

            .sidebar-logo img {
                display: block;
                width: 100%;
                max-width: 210px;
                height: auto;
            }

            .user-session-badge,
            .db-target-badge {
                display: flex;
                width: 100%;
                margin: 0 0 0.85rem 0;
                padding: 0.75rem 0.85rem;
                border: 1px solid var(--tacom-border);
                border-radius: 8px;
                background: var(--tacom-panel);
                color: var(--tacom-text);
                box-shadow: inset 0 1px 0 color-mix(in srgb, var(--tacom-text) 4%, transparent);
            }

            .user-session-badge {
                flex-direction: column;
                min-height: 48px;
                line-height: 1.2;
            }

            .user-session-name {
                font-size: 0.86rem;
                font-weight: 760;
            }

            .user-session-role {
                margin-top: 0.18rem;
                color: var(--tacom-muted);
                font-size: 0.74rem;
            }

            .db-target-badge {
                align-items: center;
                gap: 0.55rem;
                min-height: 40px;
                margin-bottom: 1.15rem;
            }

            .db-target-dot {
                width: 0.62rem;
                height: 0.62rem;
                border-radius: 999px;
                flex: 0 0 0.62rem;
                background: var(--tacom-muted-2);
                box-shadow: 0 0 0 4px rgba(102, 117, 138, 0.16);
            }

            .db-target-neon .db-target-dot {
                background: var(--tacom-secondary);
                box-shadow: 0 0 0 4px rgba(32, 208, 232, 0.18);
            }

            .db-target-local .db-target-dot {
                background: var(--tacom-success);
                box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.18);
            }

            .db-target-remote .db-target-dot {
                background: var(--tacom-primary);
                box-shadow: 0 0 0 4px rgba(20, 120, 255, 0.18);
            }

            .db-target-copy {
                min-width: 0;
                display: flex;
                flex-direction: column;
                line-height: 1.15;
            }

            .db-target-title {
                font-size: 0.76rem;
                font-weight: 760;
            }

            .db-target-label {
                max-width: 100%;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                color: var(--tacom-muted);
                font-size: 0.7rem;
            }

            section[data-testid="stSidebar"] h3 {
                margin-top: 1.1rem;
                color: var(--tacom-muted);
                font-size: 0.72rem;
                font-weight: 760;
                text-transform: uppercase;
            }

            section[data-testid="stSidebar"] details {
                border: 1px solid var(--tacom-border);
                border-radius: 8px;
                background: color-mix(in srgb, var(--tacom-panel) 92%, transparent);
                overflow: hidden;
            }

            section[data-testid="stSidebar"] details summary {
                color: var(--tacom-text);
                font-weight: 760;
            }

            section[data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
                border-top: 1px solid var(--tacom-border);
                padding-top: 0.45rem;
            }

            div[data-testid="stSidebarContent"] .stButton > button,
            div[data-testid="stSidebarContent"] button[data-testid="stBaseButton-secondary"] {
                display: flex !important;
                align-items: center !important;
                justify-content: flex-start !important;
                gap: 0.7rem;
                width: 100%;
                min-height: 2.55rem;
                padding: 0.55rem 0.75rem;
                border: 1px solid transparent;
                border-radius: 8px;
                background: transparent;
                color: var(--tacom-muted);
                font-weight: 620;
                text-align: left;
                box-shadow: none;
            }

            div[data-testid="stSidebarContent"] .stButton > button p,
            div[data-testid="stSidebarContent"] button[data-testid="stBaseButton-secondary"] p,
            div[data-testid="stSidebarContent"] button[data-testid="stBaseButton-primary"] p {
                width: 100%;
                margin: 0;
                color: inherit;
                font-size: 0.88rem;
                line-height: 1.22;
                text-align: left;
                white-space: normal;
            }

            div[data-testid="stSidebarContent"] .stButton > button [data-testid="stIconMaterial"],
            div[data-testid="stSidebarContent"] button span[data-testid="stIconMaterial"] {
                flex: 0 0 1.1rem;
                width: 1.1rem;
                min-width: 1.1rem;
                margin: 0;
                text-align: center;
            }

            div[data-testid="stSidebarContent"] .stButton > button:hover,
            div[data-testid="stSidebarContent"] button[data-testid="stBaseButton-secondary"]:hover {
                border-color: var(--tacom-border);
                background: var(--tacom-panel-hover);
                color: var(--tacom-text);
            }

            div[data-testid="stSidebarContent"] button[data-testid="stBaseButton-primary"] {
                display: flex !important;
                align-items: center !important;
                justify-content: flex-start !important;
                gap: 0.7rem;
                width: 100%;
                min-height: 2.55rem;
                padding: 0.55rem 0.75rem;
                border: 1px solid rgba(255, 83, 72, 0.48);
                border-radius: 8px;
                background: linear-gradient(135deg, var(--tacom-red-light) 0%, var(--tacom-red) 48%, var(--tacom-red-dark) 100%);
                color: #ffffff;
                font-weight: 760;
                text-align: left;
                box-shadow: 0 10px 24px rgba(255, 59, 48, 0.28);
            }

            div[data-testid="stSidebarContent"] button[data-testid="stBaseButton-primary"]:hover {
                border-color: rgba(255, 122, 112, 0.66);
                background: linear-gradient(135deg, #ff8a80 0%, var(--tacom-red) 45%, #b91c1c 100%);
                box-shadow: 0 12px 28px rgba(255, 59, 48, 0.34);
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] {
                width: 100%;
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] button {
                display: flex !important;
                align-items: center !important;
                justify-content: flex-start !important;
                width: 100% !important;
                min-width: 0 !important;
                padding-left: 0.85rem !important;
                padding-right: 0.85rem !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] button > div {
                display: flex !important;
                align-items: center !important;
                justify-content: flex-start !important;
                gap: 0.7rem !important;
                width: 100% !important;
                min-width: 0 !important;
                text-align: left !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] button p {
                flex: 1 1 auto !important;
                width: auto !important;
                min-width: 0 !important;
                margin: 0 !important;
                text-align: left !important;
                white-space: normal !important;
                overflow-wrap: normal !important;
                word-break: normal !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] button span[class*="material"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] button span[data-testid*="Icon"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] button svg {
                flex: 0 0 1.1rem !important;
                width: 1.1rem !important;
                min-width: 1.1rem !important;
                margin: 0 !important;
                text-align: center !important;
            }

            .kpi-card {
                position: relative;
                min-height: 118px;
                padding: 1.15rem 1.15rem 1rem 1.15rem;
                overflow: hidden;
                border: 1px solid var(--tacom-border) !important;
                border-radius: 8px;
                background:
                    linear-gradient(145deg, var(--tacom-panel-strong), var(--tacom-panel)) !important;
                box-shadow: var(--tacom-glow) !important;
            }

            .kpi-card::before {
                content: "";
                position: absolute;
                left: 0;
                top: 0;
                width: 100%;
                height: 2px;
                background: linear-gradient(90deg, var(--tacom-red-light), var(--tacom-red), var(--tacom-red-dark));
                opacity: 0.9;
            }

            .kpi-card::after {
                content: "⚙️";
                position: absolute;
                right: 1rem;
                top: 1.1rem;
                width: 2.35rem;
                height: 2.35rem;
                border-radius: 8px;
                background:
                    linear-gradient(135deg, var(--tacom-red-light) 0%, var(--tacom-red) 48%, var(--tacom-red-dark) 100%);
                box-shadow: 0 12px 28px rgba(255, 59, 48, 0.32);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.4rem;
                color: white;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }

            .kpi-title {
                position: relative;
                z-index: 1;
                max-width: calc(100% - 3.1rem);
                margin-bottom: 0.6rem;
                color: var(--tacom-muted);
                font-size: 0.8rem;
                font-weight: 650;
                line-height: 1.25;
            }

            .kpi-value {
                position: relative;
                z-index: 1;
                color: var(--tacom-text);
                font-size: clamp(1.7rem, 2.2vw, 2.2rem);
                font-weight: 780;
                line-height: 1;
            }

            .section-card,
            div[data-testid="stVerticalBlockBorderWrapper"] {
                border: 1px solid var(--tacom-border);
                border-radius: 8px;
                background:
                    linear-gradient(145deg, var(--tacom-panel), var(--tacom-bg-soft));
                box-shadow: var(--tacom-shadow);
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                padding: 0.35rem;
            }

            div[data-testid="stPlotlyChart"] {
                border-radius: 8px;
                overflow: hidden;
            }

            div[data-testid="stDataFrame"],
            div[data-testid="stTable"] {
                border: 1px solid var(--tacom-border);
                border-radius: 8px;
                overflow: hidden;
                background: var(--tacom-panel);
                box-shadow: var(--tacom-shadow);
            }

            div[data-testid="stMetric"],
            div[data-testid="stAlert"] {
                border-radius: 8px;
            }

            .stSelectbox label,
            .stMultiSelect label,
            .stSlider label,
            .stCheckbox label,
            .stDateInput label {
                color: var(--tacom-muted);
                font-size: 0.78rem;
                font-weight: 650;
            }

            div[data-baseweb="select"] > div,
            div[data-baseweb="input"] > div,
            div[data-baseweb="textarea"] textarea {
                border-color: var(--tacom-border) !important;
                border-radius: 8px !important;
                background-color: var(--tacom-input-bg) !important;
                color: var(--tacom-text) !important;
                box-shadow: none !important;
            }

            div[data-baseweb="select"] > div:hover,
            div[data-baseweb="input"] > div:hover,
            div[data-baseweb="textarea"] textarea:hover {
                border-color: var(--tacom-border-strong) !important;
            }

            div[data-baseweb="select"] span,
            div[data-baseweb="select"] input,
            div[data-baseweb="input"] input,
            textarea {
                color: var(--tacom-text) !important;
                -webkit-text-fill-color: var(--tacom-text) !important;
            }

            div[data-baseweb="select"] input::placeholder,
            div[data-baseweb="input"] input::placeholder,
            textarea::placeholder {
                color: var(--tacom-muted) !important;
                -webkit-text-fill-color: var(--tacom-muted) !important;
                opacity: 0.92 !important;
            }

            div[data-baseweb="select"] svg,
            div[data-baseweb="checkbox"] svg {
                color: var(--tacom-muted) !important;
            }

            div[data-baseweb="tag"] {
                border-radius: 6px !important;
                background: color-mix(in srgb, var(--tacom-primary) 18%, transparent) !important;
                color: var(--tacom-text) !important;
            }

            [data-baseweb="popover"] ul,
            [data-baseweb="popover"] [role="listbox"],
            [data-baseweb="menu"] {
                border: 1px solid var(--tacom-border) !important;
                border-radius: 8px !important;
                background: var(--tacom-panel) !important;
                color: var(--tacom-text) !important;
                box-shadow: var(--tacom-shadow) !important;
            }

            [data-baseweb="popover"],
            [data-baseweb="popover"] div,
            [data-baseweb="popover"] span,
            [data-baseweb="popover"] li,
            [data-baseweb="popover"] [role="option"],
            [data-baseweb="menu"] li,
            [data-baseweb="menu"] li div,
            [data-baseweb="menu"] li span {
                color: var(--tacom-text) !important;
                -webkit-text-fill-color: var(--tacom-text) !important;
                opacity: 1 !important;
            }

            [data-baseweb="popover"] [role="option"][aria-selected="true"],
            [data-baseweb="popover"] [role="option"][aria-selected="true"] *,
            [data-baseweb="menu"] li[aria-selected="true"],
            [data-baseweb="menu"] li[aria-selected="true"] * {
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }

            [data-baseweb="popover"] [role="option"]:hover,
            [data-baseweb="menu"] li:hover {
                background: color-mix(in srgb, var(--tacom-primary) 18%, transparent) !important;
            }

            .stCheckbox [data-baseweb="checkbox"] {
                border-radius: 5px;
            }

            .stSlider [data-baseweb="slider"] div {
                color: var(--tacom-primary);
            }

            .stButton > button,
            button[data-testid="stBaseButton-secondary"] {
                border: 1px solid var(--tacom-border);
                border-radius: 8px;
                background: var(--tacom-panel);
                color: var(--tacom-text);
                font-weight: 700;
                box-shadow: none;
            }

            .stButton > button:hover,
            button[data-testid="stBaseButton-secondary"]:hover {
                border-color: var(--tacom-border-strong);
                background: var(--tacom-panel-hover);
                color: var(--tacom-text);
            }

            button[data-testid="stBaseButton-primary"] {
                border: 1px solid rgba(57, 147, 255, 0.45);
                border-radius: 8px;
                background: linear-gradient(135deg, var(--tacom-primary), #1047c8);
                color: #ffffff;
                font-weight: 760;
                box-shadow: 0 12px 26px rgba(20, 120, 255, 0.28);
            }

            button[data-testid="stBaseButton-primary"] *,
            div[data-testid="stSidebarContent"] button[data-testid="stBaseButton-primary"] * {
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }

            button[data-testid="stBaseButton-primary"]:hover {
                border-color: rgba(32, 208, 232, 0.62);
                background: linear-gradient(135deg, #2592ff, #1158ea);
            }

            hr {
                border-color: var(--tacom-border);
            }

            ::-webkit-scrollbar {
                width: 10px;
                height: 10px;
            }

            ::-webkit-scrollbar-track {
                background: var(--tacom-bg);
            }

            ::-webkit-scrollbar-thumb {
                border: 2px solid var(--tacom-bg);
                border-radius: 999px;
                background: var(--tacom-muted-2);
            }

            ::-webkit-scrollbar-thumb:hover {
                background: rgba(32, 208, 232, 0.55);
            }

            @media (max-width: 768px) {
                .stApp {
                    --mobile-sidebar-width: min(86vw, 320px);
                }

                header[data-testid="stHeader"] {
                    height: 3rem;
                }

                div[data-testid="stAppViewContainer"] {
                    overflow-x: hidden !important;
                    overflow-y: hidden !important;
                }

                .block-container {
                    padding: 0.85rem 0.85rem 4.5rem 0.85rem;
                }

                section[data-testid="stSidebar"] {
                    width: var(--mobile-sidebar-width) !important;
                    min-width: var(--mobile-sidebar-width) !important;
                    max-width: var(--mobile-sidebar-width) !important;
                    flex: 0 0 var(--mobile-sidebar-width) !important;
                    box-shadow: none !important;
                    z-index: 20 !important;
                }

                section[data-testid="stSidebar"][aria-expanded="true"] {
                    transform: none !important;
                }

                section[data-testid="stSidebar"][aria-expanded="false"] {
                    width: 0 !important;
                    min-width: 0 !important;
                    max-width: 0 !important;
                    flex-basis: 0 !important;
                    border-right: 0;
                }

                div[data-testid="stAppViewContainer"]:has(
                    section[data-testid="stSidebar"][aria-expanded="true"]
                ) .stMain,
                div[data-testid="stAppViewContainer"]:has(
                    section[data-testid="stSidebar"][aria-expanded="true"]
                ) section[data-testid="stAppScrollToBottomContainer"] {
                    transform: translateX(var(--mobile-sidebar-width)) !important;
                }

                .stMain,
                section[data-testid="stAppScrollToBottomContainer"] {
                    transition: transform 300ms ease;
                    width: 100vw !important;
                }

                section[data-testid="stSidebar"] > div,
                div[data-testid="stSidebarContent"] {
                    width: var(--mobile-sidebar-width) !important;
                    min-width: var(--mobile-sidebar-width) !important;
                    max-width: var(--mobile-sidebar-width) !important;
                }

                div[data-testid="stSidebarContent"] {
                    padding: 0.85rem 0.75rem 1rem 0.75rem;
                }

                div[data-testid="stSidebarContent"] img {
                    max-width: 175px !important;
                }

                .main-title {
                    margin-top: 0.4rem;
                    font-size: 1.35rem;
                }

                .kpi-card {
                    min-height: 104px;
                    padding: 1rem;
                }

                .kpi-card::after {
                    width: 2rem;
                    height: 2rem;
                }

                .kpi-title {
                    font-size: 0.76rem;
                }

                .kpi-value {
                    font-size: 1.55rem;
                }

                div[data-testid="stHorizontalBlock"] {
                    gap: 0.75rem;
                    flex-wrap: wrap;
                }

                div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }

                div[data-testid="stPlotlyChart"] {
                    min-width: 0 !important;
                    overflow-x: auto;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_titulo_principal(titulo: str) -> None:
    st.markdown(f'<div class="main-title">{titulo}</div>', unsafe_allow_html=True)
