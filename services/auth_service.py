import hashlib
import secrets
from datetime import datetime, timedelta
from database import get_connection


class AuthService:
    """Lógica de autenticação com hash de senha + salt e tokens de sessão."""

    SESSION_DURATION_HOURS = 72  # Sessão dura 3 dias
    PBKDF2_ITERATIONS = 600_000  # OWASP recommendation

    @staticmethod
    def _hash_password(password, salt):
        """Gera hash PBKDF2-SHA256 da senha + salt (600k iterações)."""
        return hashlib.pbkdf2_hmac(
            'sha256', password.encode(), salt.encode(),
            AuthService.PBKDF2_ITERATIONS
        ).hex()

    @staticmethod
    def _hash_password_legacy(password, salt):
        """Hash SHA-256 legado — usado apenas para migração de senhas antigas."""
        return hashlib.sha256((password + salt).encode()).hexdigest()

    @staticmethod
    def login(username, password):
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
            legacy_hash = AuthService._hash_password_legacy(password, user['salt'])
            if legacy_hash != user['password_hash']:
                conn.close()
                raise ValueError("Usuário ou senha incorretos")
            new_salt = secrets.token_hex(32)
            new_hash = AuthService._hash_password(password, new_salt)
            cursor.execute(
                "UPDATE usuarios SET password_hash = ?, salt = ? WHERE id = ?",
                (new_hash, new_salt, user['id'])
            )

        AuthService._limpar_sessoes_expiradas_internal(cursor)

        token = secrets.token_hex(32)
        expira_em = (datetime.now() + timedelta(hours=AuthService.SESSION_DURATION_HOURS)).isoformat()

        cursor.execute(
            "INSERT INTO sessoes (usuario_id, token, criado_em, expira_em) VALUES (?, ?, ?, ?)",
            (user['id'], token, datetime.now().isoformat(), expira_em)
        )

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

        hash_atual = AuthService._hash_password(senha_atual, user['salt'])
        if hash_atual != user['password_hash']:
            legacy_hash = AuthService._hash_password_legacy(senha_atual, user['salt'])
            if legacy_hash != user['password_hash']:
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
    def _limpar_sessoes_expiradas_internal(cursor):
        """Remove sessões expiradas (usa cursor existente)."""
        try:
            cursor.execute("DELETE FROM sessoes WHERE expira_em < ?", (datetime.now().isoformat(),))
        except Exception:
            pass

    @staticmethod
    def limpar_sessoes_expiradas():
        """Remove sessões expiradas do banco."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessoes WHERE expira_em < ?", (datetime.now().isoformat(),))
        conn.commit()
        conn.close()

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
        if len(username.strip()) > 50:
            raise ValueError("Usuário deve ter no máximo 50 caracteres")
        if not password or len(password) < 4:
            raise ValueError("Senha deve ter no mínimo 4 caracteres")
        if not nome or not nome.strip():
            raise ValueError("Nome é obrigatório")
        if len(nome.strip()) > 100:
            raise ValueError("Nome deve ter no máximo 100 caracteres")

        username = username.strip().lower()

        conn = get_connection()
        cursor = conn.cursor()

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
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            raise ValueError("Usuário não encontrado")

        if user['is_admin']:
            cursor.execute("SELECT COUNT(*) as count FROM usuarios WHERE is_admin = 1")
            if cursor.fetchone()['count'] <= 1:
                conn.close()
                raise ValueError("Não é possível remover o último administrador")

        cursor.execute("DELETE FROM sessoes WHERE usuario_id = ?", (usuario_id,))
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def atualizar_usuario(usuario_id, nome=None, is_admin=None, nova_senha=None):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            raise ValueError("Usuário não encontrado")

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
            cursor.execute("DELETE FROM sessoes WHERE usuario_id = ?", (usuario_id,))

        conn.commit()
        conn.close()
