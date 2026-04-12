import pandas as pd
import streamlit as st


def _abrir_secao() -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)


def _fechar_secao() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_tabela_resumo(df_resumo: pd.DataFrame) -> None:
    _abrir_secao()
    st.subheader("Resumo por Equipamento")
    st.dataframe(
        df_resumo.sort_values("percentual_recalculado", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
    _fechar_secao()


def render_tabela_evolucao(df_evolucao: pd.DataFrame) -> None:
    _abrir_secao()
    st.subheader("Evolucao Mensal")
    st.dataframe(
        df_evolucao.sort_values(["mes", "equipamento"]),
        use_container_width=True,
        hide_index=True,
    )
    _fechar_secao()


def render_tabela_detalhe(df_filtrado: pd.DataFrame) -> None:
    _abrir_secao()
    st.subheader("Base Filtrada")
    df_view = df_filtrado.copy()
    if "data_ref" in df_view.columns:
        df_view["data_ref"] = pd.to_datetime(df_view["data_ref"], errors="coerce").dt.strftime("%Y-%m-%d")
    st.dataframe(
        df_view.sort_values("data_ref", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
    _fechar_secao()
