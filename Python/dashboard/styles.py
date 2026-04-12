import streamlit as st


def aplicar_estilos_globais() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background: #f3f6fb;
                color: #0f172a;
            }

            section[data-testid="stSidebar"] {
                background: #ffffff;
                border-right: 1px solid #e2e8f0;
            }

            .block-container {
                padding-top: 1rem;
                padding-bottom: 1rem;
            }

            .main-title {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 24px;
                font-weight: 700;
                color: #0f172a;
                margin-bottom: 1rem;
            }

            .kpi-card {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px;
                min-height: 96px;
            }

            .kpi-title {
                font-size: 13px;
                color: #475569;
                margin-bottom: 8px;
                font-weight: 600;
            }

            .kpi-value {
                font-size: 28px;
                font-weight: 700;
                color: #0f172a;
                line-height: 1.05;
            }

            .section-card {
                background: #ffffff;
                border: 1px solid #e2e8f0;
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
