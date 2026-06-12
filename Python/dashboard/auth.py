import hmac
import base64
import hashlib
import json
import os
import time
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from dashboard.config import PERFIL_ADMIN, USUARIOS_APP

load_dotenv()

USUARIO_LOGADO_KEY = "usuario_logado"
AUTH_SESSION_TOKEN_KEY = "auth_session_token"
AUTH_CLEAR_BROWSER_FLAG_KEY = "auth_clear_browser_storage"
AUTH_COOKIE_KEY = "tacom_dashboard_auth_token"
AUTH_TOKEN_TTL_HOURS = 12
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


def _base64url_encode(valor: bytes) -> str:
    return base64.urlsafe_b64encode(valor).decode("ascii").rstrip("=")


def _base64url_decode(valor: str) -> bytes:
    padding = "=" * (-len(valor) % 4)
    return base64.urlsafe_b64decode(f"{valor}{padding}".encode("ascii"))


def _auth_secret() -> bytes:
    segredo_configurado = os.getenv("DASHBOARD_AUTH_SECRET", "").strip()
    if segredo_configurado:
        return segredo_configurado.encode("utf-8")

    material_usuarios = "|".join(
        f"{usuario}:{dados.get('senha', '')}:{dados.get('perfil', '')}"
        for usuario, dados in sorted(USUARIOS_APP.items())
    )
    return hashlib.sha256(
        f"dashboard-auth:{material_usuarios}".encode("utf-8")
    ).digest()


def _token_ttl_segundos() -> int:
    ttl_horas = os.getenv("DASHBOARD_AUTH_TTL_HOURS", "").strip()
    if not ttl_horas:
        return AUTH_TOKEN_TTL_HOURS * 60 * 60

    try:
        return max(1, int(float(ttl_horas) * 60 * 60))
    except ValueError:
        return AUTH_TOKEN_TTL_HOURS * 60 * 60


def _fingerprint_senha(dados_usuario: dict[str, Any]) -> str:
    senha = str(dados_usuario.get("senha") or "")
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def _criar_token_login(usuario: str, dados_usuario: dict[str, Any]) -> str:
    payload = {
        "usuario": usuario,
        "exp": int(time.time()) + _token_ttl_segundos(),
        "senha_fp": _fingerprint_senha(dados_usuario),
    }
    payload_json = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    payload_b64 = _base64url_encode(payload_json)
    assinatura = hmac.new(
        _auth_secret(),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_b64}.{_base64url_encode(assinatura)}"


def _validar_token_login(token: object) -> dict[str, Any] | None:
    if not isinstance(token, str) or "." not in token:
        return None

    try:
        payload_b64, assinatura_b64 = token.split(".", 1)
        assinatura_esperada = _base64url_encode(
            hmac.new(
                _auth_secret(),
                payload_b64.encode("ascii"),
                hashlib.sha256,
            ).digest()
        )
        if not hmac.compare_digest(assinatura_b64, assinatura_esperada):
            return None

        payload = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    usuario = _normalizar_usuario(str(payload.get("usuario") or ""))
    dados_usuario = USUARIOS_APP.get(usuario)
    if not dados_usuario:
        return None

    expira_em = int(payload.get("exp") or 0)
    if expira_em < int(time.time()):
        return None

    if not hmac.compare_digest(
        str(payload.get("senha_fp") or ""),
        _fingerprint_senha(dados_usuario),
    ):
        return None

    return _dados_publicos_usuario(usuario, dados_usuario)


def _render_cookie_script(codigo: str) -> None:
    components.html(
        f"""
        <script>
        (() => {{
            {codigo}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def _salvar_token_no_browser(token: str) -> None:
    _render_cookie_script(
        f"""
            document.cookie = [
                {json.dumps(AUTH_COOKIE_KEY)} + "=" + encodeURIComponent({json.dumps(token)}),
                "Max-Age=" + {str(_token_ttl_segundos())},
                "Path=/",
                "SameSite=Lax"
            ].join("; ");
        """
    )


def _limpar_token_do_browser() -> None:
    _render_cookie_script(
        f"""
            document.cookie = [
                {json.dumps(AUTH_COOKIE_KEY)} + "=",
                "Max-Age=0",
                "Path=/",
                "SameSite=Lax"
            ].join("; ");
        """
    )


def _restaurar_login_por_cookie() -> dict[str, Any] | None:
    token = st.context.cookies.get(AUTH_COOKIE_KEY, "")
    if not token:
        return None

    usuario_logado = _validar_token_login(token)
    if not usuario_logado:
        st.session_state[AUTH_CLEAR_BROWSER_FLAG_KEY] = True
        return None

    st.session_state[USUARIO_LOGADO_KEY] = usuario_logado
    st.session_state[AUTH_SESSION_TOKEN_KEY] = token
    return usuario_logado


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
    st.session_state[AUTH_SESSION_TOKEN_KEY] = _criar_token_login(
        usuario_normalizado,
        dados_usuario,
    )
    return True


def obter_usuario_logado() -> dict[str, Any] | None:
    usuario_logado = st.session_state.get(USUARIO_LOGADO_KEY)
    if isinstance(usuario_logado, dict):
        token = st.session_state.get(AUTH_SESSION_TOKEN_KEY)
        if isinstance(token, str) and token:
            usuario_por_token = _validar_token_login(token)
            if usuario_por_token:
                st.session_state[USUARIO_LOGADO_KEY] = usuario_por_token
                return usuario_por_token

            st.session_state.pop(USUARIO_LOGADO_KEY, None)
            st.session_state.pop(AUTH_SESSION_TOKEN_KEY, None)
            st.session_state[AUTH_CLEAR_BROWSER_FLAG_KEY] = True
            return None

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
    st.session_state.pop(AUTH_SESSION_TOKEN_KEY, None)
    st.session_state[AUTH_CLEAR_BROWSER_FLAG_KEY] = True


def render_login() -> dict[str, Any]:
    limpar_browser = False
    if st.session_state.pop(AUTH_CLEAR_BROWSER_FLAG_KEY, False):
        limpar_browser = True
        _limpar_token_do_browser()

    usuario_logado = obter_usuario_logado()
    if not usuario_logado:
        usuario_logado = _restaurar_login_por_cookie()
        if st.session_state.pop(AUTH_CLEAR_BROWSER_FLAG_KEY, False):
            limpar_browser = True
            _limpar_token_do_browser()

    if usuario_logado:
        token = st.session_state.get(AUTH_SESSION_TOKEN_KEY)
        if not isinstance(token, str) or not token:
            usuario = _normalizar_usuario(str(usuario_logado.get("usuario") or ""))
            dados_usuario = USUARIOS_APP.get(usuario)
            if dados_usuario:
                token = _criar_token_login(usuario, dados_usuario)
                st.session_state[AUTH_SESSION_TOKEN_KEY] = token
        if isinstance(token, str) and token:
            _salvar_token_no_browser(token)
        return usuario_logado

    if not limpar_browser:
        _restaurar_login_por_cookie()

    col_esquerda, col_centro, col_direita = st.columns([1, 1.2, 1])
    with col_centro:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 1rem;">
                <h2 style="margin-bottom: 0.25rem;">Login</h2>
                <p style="margin: 0; opacity: 0.75;">
                    Informe seu usuario e senha para acessar o dashboard.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("form_login"):
            st.markdown(
                '<div class="login-form-marker"></div>',
                unsafe_allow_html=True,
            )
            usuario = st.text_input("Usuario")
            senha = st.text_input("Senha", type="password")
            enviar = st.form_submit_button("Entrar", type="primary", use_container_width=True)

        if enviar:
            if autenticar_usuario(usuario, senha):
                st.rerun()

            st.error("Usuario ou senha invalidos.")

    st.stop()
