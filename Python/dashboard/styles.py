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
                padding-bottom: 1rem;
            }

            .main-title {
                background: var(--secondary-background-color);
                border: 1px solid rgba(127, 127, 127, 0.25);
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 24px;
                font-weight: 700;
                color: var(--text-color);
                margin-bottom: 1rem;
                margin-top: 2rem;
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_titulo_principal(titulo: str) -> None:
    st.markdown(f'<div class="main-title">{titulo}</div>', unsafe_allow_html=True)
