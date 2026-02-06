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
                'nome': user['nome'],
                'is_admin': bool(user['is_admin'])
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
            SELECT s.*, u.username, u.nome, u.is_admin
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
            'nome': sessao['nome'],
            'is_admin': bool(sessao['is_admin']) if 'is_admin' in sessao.keys() else False
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

    # ═══════════════════════════════════════════
    # GERENCIAMENTO DE CONTAS (Admin)
    # ═══════════════════════════════════════════

    @staticmethod
    def listar_usuarios():
        """Retorna lista de todos os usuários (sem dados sensíveis)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, nome, is_admin, criado_em, ultimo_login FROM usuarios ORDER BY criado_em"
        )
        usuarios = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return usuarios

    @staticmethod
    def criar_usuario(username, password, nome, is_admin=False):
        """
        Cria um novo usuário.

        Args:
            username: Login único.
            password: Senha (mín 4 caracteres).
            nome: Nome de exibição.
            is_admin: Se é administrador.

        Returns:
            dict com dados do novo usuário.

        Raises:
            ValueError: Se dados inválidos ou username já existe.
        """
        if not username or len(username.strip()) < 3:
            raise ValueError("Usuário deve ter no mínimo 3 caracteres")
        if not password or len(password) < 4:
            raise ValueError("Senha deve ter no mínimo 4 caracteres")
        if not nome or not nome.strip():
            raise ValueError("Nome é obrigatório")

        username = username.strip().lower()

        conn = get_connection()
        cursor = conn.cursor()

        # Verificar se username já existe
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            raise ValueError(f"Usuário '{username}' já existe")

        salt = secrets.token_hex(32)
        password_hash = AuthService._hash_password(password, salt)

        cursor.execute(
            "INSERT INTO usuarios (username, password_hash, salt, nome, is_admin) VALUES (?, ?, ?, ?, ?)",
            (username, password_hash, salt, nome.strip(), 1 if is_admin else 0)
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            'id': user_id,
            'username': username,
            'nome': nome.strip(),
            'is_admin': bool(is_admin)
        }

    @staticmethod
    def deletar_usuario(usuario_id):
        """
        Remove um usuário e todas as suas sessões.

        Args:
            usuario_id: ID do usuário a remover.

        Raises:
            ValueError: Se tentar deletar o último admin ou usuário não existe.
        """
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            raise ValueError("Usuário não encontrado")

        # Não permitir deletar o último admin
        if user['is_admin']:
            cursor.execute("SELECT COUNT(*) as count FROM usuarios WHERE is_admin = 1")
            if cursor.fetchone()['count'] <= 1:
                conn.close()
                raise ValueError("Não é possível remover o último administrador")

        # Remover sessões e usuário
        cursor.execute("DELETE FROM sessoes WHERE usuario_id = ?", (usuario_id,))
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def atualizar_usuario(usuario_id, nome=None, is_admin=None, nova_senha=None):
        """
        Atualiza dados de um usuário (para o admin).

        Args:
            usuario_id: ID do usuário.
            nome: Novo nome (ou None para não alterar).
            is_admin: Novo status admin (ou None para não alterar).
            nova_senha: Nova senha (ou None para não alterar).
        """
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            raise ValueError("Usuário não encontrado")

        # Se estiver removendo admin, verificar se não é o último
        if is_admin is not None and not is_admin and user['is_admin']:
            cursor.execute("SELECT COUNT(*) as count FROM usuarios WHERE is_admin = 1")
            if cursor.fetchone()['count'] <= 1:
                conn.close()
                raise ValueError("Não é possível remover o último administrador")

        if nome is not None:
            cursor.execute("UPDATE usuarios SET nome = ? WHERE id = ?", (nome.strip(), usuario_id))

        if is_admin is not None:
            cursor.execute("UPDATE usuarios SET is_admin = ? WHERE id = ?", (1 if is_admin else 0, usuario_id))

        if nova_senha is not None:
            if len(nova_senha) < 4:
                conn.close()
                raise ValueError("Senha deve ter no mínimo 4 caracteres")
            novo_salt = secrets.token_hex(32)
            novo_hash = AuthService._hash_password(nova_senha, novo_salt)
            cursor.execute(
                "UPDATE usuarios SET password_hash = ?, salt = ? WHERE id = ?",
                (novo_hash, novo_salt, usuario_id)
            )
            # Invalidar sessões
            cursor.execute("DELETE FROM sessoes WHERE usuario_id = ?", (usuario_id,))

        conn.commit()
        conn.close()
