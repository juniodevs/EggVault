"""Serviço de autenticação — login, sessões e gerenciamento de usuários."""

import hashlib
import secrets
from datetime import datetime, timedelta
from database import get_connection


class AuthService:
    """Lógica de autenticação com hash de senha + salt e tokens de sessão."""

    SESSION_DURATION_HOURS = 72  # Sessão dura 3 dias

    @staticmethod
    def _hash_password(password, salt):
        """Gera hash SHA-256 da senha + salt."""
        return hashlib.sha256((password + salt).encode()).hexdigest()

    @staticmethod
    def login(username, password):
        """
        Autentica usuário e retorna token de sessão.

        Returns:
            dict com token e dados do usuário.

        Raises:
            ValueError: Se credenciais inválidas.
        """
        if not username or not password:
            raise ValueError("Usuário e senha são obrigatórios")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM usuarios WHERE username = ?", (username.strip().lower(),)
        )
        user = cursor.fetchone()

        if not user:
            conn.close()
            raise ValueError("Usuário ou senha incorretos")

        password_hash = AuthService._hash_password(password, user['salt'])
        if password_hash != user['password_hash']:
            conn.close()
            raise ValueError("Usuário ou senha incorretos")

        # Criar sessão
        token = secrets.token_hex(32)
        expira_em = (datetime.now() + timedelta(hours=AuthService.SESSION_DURATION_HOURS)).isoformat()

        cursor.execute(
            "INSERT INTO sessoes (usuario_id, token, criado_em, expira_em) VALUES (?, ?, ?, ?)",
            (user['id'], token, datetime.now().isoformat(), expira_em)
        )

        # Atualizar último login
        cursor.execute(
            "UPDATE usuarios SET ultimo_login = ? WHERE id = ?",
            (datetime.now().isoformat(), user['id'])
        )

        conn.commit()
        conn.close()

        return {
            'token': token,
            'usuario': {
                'id': user['id'],
                'username': user['username'],
                'nome': user['nome']
            },
            'expira_em': expira_em
        }

    @staticmethod
    def validar_token(token):
        """
        Valida um token de sessão.

        Returns:
            dict com dados do usuário se válido, None se inválido.
        """
        if not token:
            return None

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, u.username, u.nome
            FROM sessoes s
            JOIN usuarios u ON s.usuario_id = u.id
            WHERE s.token = ? AND s.expira_em > ?
        """, (token, datetime.now().isoformat()))
        sessao = cursor.fetchone()
        conn.close()

        if not sessao:
            return None

        return {
            'id': sessao['usuario_id'],
            'username': sessao['username'],
            'nome': sessao['nome']
        }

    @staticmethod
    def logout(token):
        """Remove a sessão (logout)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessoes WHERE token = ?", (token,))
        conn.commit()
        conn.close()

    @staticmethod
    def alterar_senha(usuario_id, senha_atual, nova_senha):
        """
        Altera a senha de um usuário.

        Raises:
            ValueError: Se senha atual incorreta ou nova senha inválida.
        """
        if not nova_senha or len(nova_senha) < 4:
            raise ValueError("Nova senha deve ter pelo menos 4 caracteres")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            raise ValueError("Usuário não encontrado")

        # Verificar senha atual
        hash_atual = AuthService._hash_password(senha_atual, user['salt'])
        if hash_atual != user['password_hash']:
            conn.close()
            raise ValueError("Senha atual incorreta")

        # Gerar novo salt e hash
        novo_salt = secrets.token_hex(32)
        novo_hash = AuthService._hash_password(nova_senha, novo_salt)

        cursor.execute(
            "UPDATE usuarios SET password_hash = ?, salt = ? WHERE id = ?",
            (novo_hash, novo_salt, usuario_id)
        )

        # Invalidar todas as sessões do usuário
        cursor.execute("DELETE FROM sessoes WHERE usuario_id = ?", (usuario_id,))

        conn.commit()
        conn.close()

    @staticmethod
    def limpar_sessoes_expiradas():
        """Remove sessões expiradas do banco."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessoes WHERE expira_em < ?", (datetime.now().isoformat(),))
        conn.commit()
        conn.close()
