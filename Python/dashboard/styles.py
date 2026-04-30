import streamlit as st


def aplicar_estilos_globais() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background: var(--background-color);
                color: var(--text-color);
            }

            section[data-testid="stSidebar"] {
                background: var(--secondary-background-color);
                border-right: 1px solid rgba(127, 127, 127, 0.25);
            }

            div[data-testid="stSidebarContent"] {
                padding-top: 0.75rem;
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

            div[data-testid="stLogoSpacer"] {
                display: none !important;
            }

            div[data-testid="stSidebarUserContent"] {
                padding-top: 0 !important;
            }

            div[data-testid="stMarkdownContainer"]:has(.sidebar-logo) {
                margin-bottom: 0 !important;
            }

            .sidebar-logo {
                margin: 0 0 14px 0;
            }

            .sidebar-logo img {
                display: block;
                width: 100%;
                max-width: 220px;
                height: auto;
            }

            header[data-testid="stHeader"] {
                background: var(--background-color);
                border-bottom: none;
                box-shadow: none;
            }

            div[data-testid="stDecoration"] {
                display: none;
            }

            .block-container {
                padding-top: 1rem;
                padding-right: 2rem;
                padding-bottom: 1rem;
                padding-left: 2rem;
                max-width: 100%;
            }

            .main-title {
                background: var(--secondary-background-color);
                border: 1px solid rgba(127, 127, 127, 0.25);
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 24px;
                font-weight: 700;
                line-height: 1.2;
                color: var(--text-color);
                margin-bottom: 1rem;
                margin-top: 2rem;
                overflow-wrap: anywhere;
            }

            .kpi-card {
                background: var(--secondary-background-color);
                border: 1px solid rgba(127, 127, 127, 0.25);
                border-radius: 8px;
                padding: 12px;
                min-height: 96px;
            }

            .kpi-title {
                font-size: 13px;
                color: var(--text-color);
                opacity: 0.75;
                margin-bottom: 8px;
                font-weight: 600;
            }

            .kpi-value {
                font-size: 28px;
                font-weight: 700;
                color: var(--text-color);
                line-height: 1.05;
            }

            .section-card {
                background: var(--secondary-background-color);
                border: 1px solid rgba(127, 127, 127, 0.25);
                border-radius: 8px;
                padding: 10px 12px 6px 12px;
                margin-bottom: 1rem;
            }

            .db-target-badge {
                display: flex;
                align-items: center;
                gap: 8px;
                width: 100%;
                min-height: 38px;
                margin: -10px 0 18px 0;
                padding: 8px 10px;
                border: 1px solid rgba(127, 127, 127, 0.25);
                border-radius: 8px;
                background: rgba(127, 127, 127, 0.08);
                color: var(--text-color);
            }

            .db-target-dot {
                width: 10px;
                height: 10px;
                border-radius: 999px;
                flex: 0 0 10px;
                background: #64748B;
                box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.18);
            }

            .db-target-neon .db-target-dot {
                background: #00E699;
                box-shadow: 0 0 0 3px rgba(0, 230, 153, 0.2);
            }

            .db-target-local .db-target-dot {
                background: #F59E0B;
                box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2);
            }

            .db-target-remote .db-target-dot {
                background: #38BDF8;
                box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
            }

            .db-target-copy {
                min-width: 0;
                display: flex;
                flex-direction: column;
                line-height: 1.15;
            }

            .db-target-title {
                font-size: 12px;
                font-weight: 700;
            }

            .db-target-label {
                max-width: 100%;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                font-size: 11px;
                opacity: 0.72;
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
                    padding: 0.75rem 0.85rem 4.5rem 0.85rem;
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
                    padding: 0.75rem 0.75rem 1rem 0.75rem;
                }

                div[data-testid="stSidebarContent"] img {
                    max-width: 175px !important;
                }

                .main-title {
                    margin-top: 0.75rem;
                    padding: 10px 12px;
                    font-size: 20px;
                }

                .kpi-card {
                    min-height: auto;
                    padding: 10px;
                }

                .kpi-title {
                    font-size: 12px;
                    margin-bottom: 6px;
                }

                .kpi-value {
                    font-size: 24px;
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
