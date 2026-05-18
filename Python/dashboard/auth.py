import hmac
from typing import Any

import streamlit as st

from dashboard.config import PERFIL_ADMIN, USUARIOS_APP

USUARIO_LOGADO_KEY = "usuario_logado"
PERFIS_ADMIN = {PERFIL_ADMIN, "adm"}


def _normalizar_usuario(usuario: str) -> str:
    return usuario.strip().lower()


def _dados_publicos_usuario(usuario: str, dados_usuario: dict[str, Any]) -> dict[str, Any]:
    return {
        "usuario": usuario,
        "nome": str(dados_usuario.get("nome") or usuario),
        "perfil": str(dados_usuario.get("perfil") or ""),
        "prioridade": int(dados_usuario.get("prioridade") or 0),
    }


def autenticar_usuario(usuario: str, senha: str) -> bool:
    usuario_normalizado = _normalizar_usuario(usuario)
    dados_usuario = USUARIOS_APP.get(usuario_normalizado)

    if not dados_usuario:
        return False

    senha_configurada = str(dados_usuario.get("senha") or "")
    if not hmac.compare_digest(senha, senha_configurada):
        return False

    st.session_state[USUARIO_LOGADO_KEY] = _dados_publicos_usuario(
        usuario_normalizado,
        dados_usuario,
    )
    return True


def obter_usuario_logado() -> dict[str, Any] | None:
    usuario_logado = st.session_state.get(USUARIO_LOGADO_KEY)
    if isinstance(usuario_logado, dict):
        return usuario_logado

    return None


def usuario_esta_autenticado() -> bool:
    return obter_usuario_logado() is not None


def usuario_eh_admin() -> bool:
    usuario_logado = obter_usuario_logado()
    if not usuario_logado:
        return False

    return str(usuario_logado.get("perfil") or "").lower() in PERFIS_ADMIN


def encerrar_sessao() -> None:
    st.session_state.pop(USUARIO_LOGADO_KEY, None)


def render_login() -> dict[str, Any]:
    usuario_logado = obter_usuario_logado()
    if usuario_logado:
        return usuario_logado

    col_esquerda, col_centro, col_direita = st.columns([1, 1.2, 1])
    with col_centro:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 1rem; max-width="450px">
                <h2 style="margin-bottom: 0.25rem;">Login</h2>
                <p style="margin: 0; opacity: 0.75;">
                    Informe seu usuario e senha para acessar o dashboard.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("form_login"):
            usuario = st.text_input("Usuario")
            senha = st.text_input("Senha", type="password")
            enviar = st.form_submit_button("Entrar", type="primary", use_container_width=True)

        if enviar:
            if autenticar_usuario(usuario, senha):
                st.rerun()

            st.error("Usuario ou senha invalidos.")

    st.stop()
