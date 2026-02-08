"""
🥚 EggVault — Aplicativo de Gerenciamento de Ovos
Servidor Flask com API REST e interface web SPA.
"""

from flask import Flask, render_template, request, jsonify, send_file
from functools import wraps
from database import init_db, get_connection
from services.estoque_service import EstoqueService
from services.entrada_service import EntradaService
from services.saida_service import SaidaService
from services.preco_service import PrecoService
from services.relatorio_service import RelatorioService
from services.quebrado_service import QuebradoService
from services.consumo_service import ConsumoService
from services.despesa_service import DespesaService
from services.auth_service import AuthService
from services.export_service import ExportService
from datetime import datetime

app = Flask(__name__)


# ═══════════════════════════════════════════
# MIDDLEWARE DE AUTENTICAÇÃO
# ═══════════════════════════════════════════

def login_required(f):
    """Decorator que exige autenticação via token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            token = request.cookies.get('auth_token', '')

        usuario = AuthService.validar_token(token)
        if not usuario:
            return jsonify({'success': False, 'error': 'Não autenticado', 'auth_required': True}), 401

        request.usuario = usuario
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator que exige autenticação + permissão de admin."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not request.usuario.get('is_admin'):
            return jsonify({'success': False, 'error': 'Acesso negado — apenas administradores'}), 403
        return f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════
# PÁGINA PRINCIPAL
# ═══════════════════════════════════════════

@app.route('/')
def index():
    """Serve a página principal (SPA)."""
    return render_template('index.html')


# ═══════════════════════════════════════════
# API — AUTENTICAÇÃO
# ═══════════════════════════════════════════

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Autentica usuário e retorna token."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        username = data.get('username', '')
        password = data.get('password', '')
        result = AuthService.login(username, password)

        response = jsonify({'success': True, 'data': result})
        response.set_cookie(
            'auth_token', result['token'],
            httponly=True, samesite='Strict', max_age=72*3600
        )
        return response
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    """Retorna dados do usuário logado (verifica se sessão é válida)."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('auth_token', '')

    usuario = AuthService.validar_token(token)
    if not usuario:
        return jsonify({'success': False, 'error': 'Não autenticado', 'auth_required': True}), 401

    return jsonify({'success': True, 'data': usuario})


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Encerra sessão do usuário."""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            token = request.cookies.get('auth_token', '')

        AuthService.logout(token)
        response = jsonify({'success': True, 'message': 'Logout realizado'})
        response.delete_cookie('auth_token')
        return response
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/alterar-senha', methods=['POST'])
@login_required
def auth_alterar_senha():
    """Altera a senha do usuário logado."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        AuthService.alterar_senha(
            request.usuario['id'],
            data.get('senha_atual', ''),
            data.get('nova_senha', '')
        )
        response = jsonify({'success': True, 'message': 'Senha alterada com sucesso'})
        response.delete_cookie('auth_token')
        return response
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — ESTOQUE
# ═══════════════════════════════════════════

@app.route('/api/estoque', methods=['GET'])
@login_required
def get_estoque():
    """Retorna o estoque atual com indicador de status."""
    try:
        estoque = EstoqueService.get_estoque()
        return jsonify({'success': True, 'data': estoque})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — ENTRADAS
# ═══════════════════════════════════════════

@app.route('/api/entradas', methods=['GET'])
@login_required
def get_entradas():
    """Lista entradas filtradas por mês."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        entradas = EntradaService.listar(mes)
        return jsonify({'success': True, 'data': entradas})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/entradas', methods=['POST'])
@login_required
def add_entrada():
    """Registra uma nova entrada de ovos."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        quantidade = int(data.get('quantidade', 0))
        observacao = data.get('observacao', '')
        entry_id = EntradaService.registrar(
            quantidade, observacao,
            usuario_id=request.usuario['id'],
            usuario_nome=request.usuario['nome'] or request.usuario['username']
        )
        return jsonify({
            'success': True,
            'id': entry_id,
            'message': f'{quantidade} ovos adicionados ao estoque'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — ENTRADAS (DELETE)
# ═══════════════════════════════════════════

@app.route('/api/entradas/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_entrada(entry_id):
    """Remove uma entrada e subtrai do estoque."""
    try:
        quantidade = EntradaService.remover(entry_id)
        return jsonify({
            'success': True,
            'message': f'{quantidade} ovos removidos do estoque'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — SAÍDAS / VENDAS
# ═══════════════════════════════════════════

@app.route('/api/saidas', methods=['GET'])
@login_required
def get_saidas():
    """Lista vendas filtradas por mês."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        saidas = SaidaService.listar(mes)
        return jsonify({'success': True, 'data': saidas})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/saidas', methods=['POST'])
@login_required
def add_saida():
    """Registra uma nova venda de ovos."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        quantidade = int(data.get('quantidade', 0))
        preco_unitario = data.get('preco_unitario')
        if preco_unitario is not None:
            preco_unitario = float(preco_unitario)

        sale_id = SaidaService.registrar(
            quantidade, preco_unitario,
            usuario_id=request.usuario['id'],
            usuario_nome=request.usuario['nome'] or request.usuario['username']
        )
        return jsonify({
            'success': True,
            'id': sale_id,
            'message': f'{quantidade} ovos vendidos com sucesso'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/saidas/<int:sale_id>', methods=['DELETE'])
@login_required
def delete_saida(sale_id):
    """Remove uma venda e devolve ovos ao estoque."""
    try:
        quantidade = SaidaService.remover(sale_id)
        return jsonify({
            'success': True,
            'message': f'{quantidade} ovos devolvidos ao estoque'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — PREÇOS
# ═══════════════════════════════════════════

@app.route('/api/precos', methods=['GET'])
@login_required
def get_precos():
    """Retorna o histórico de preços."""
    try:
        precos = PrecoService.historico()
        return jsonify({'success': True, 'data': precos})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/precos/ativo', methods=['GET'])
@login_required
def get_preco_ativo():
    """Retorna o preço ativo atual."""
    try:
        preco = PrecoService.get_ativo()
        return jsonify({'success': True, 'data': preco})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/precos', methods=['POST'])
@login_required
def set_preco():
    """Define um novo preço ativo."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        preco_unitario = float(data.get('preco_unitario', 0))
        price_id = PrecoService.definir_preco(preco_unitario)
        return jsonify({
            'success': True,
            'id': price_id,
            'message': f'Preço atualizado para R$ {preco_unitario:.2f}'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — OVOS QUEBRADOS
# ═══════════════════════════════════════════

@app.route('/api/quebrados', methods=['GET'])
@login_required
def get_quebrados():
    """Lista registros de ovos quebrados filtrados por mês."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        quebrados = QuebradoService.listar(mes)
        return jsonify({'success': True, 'data': quebrados})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/quebrados', methods=['POST'])
@login_required
def add_quebrado():
    """Registra ovos quebrados (perda)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        quantidade = int(data.get('quantidade', 0))
        motivo = data.get('motivo', '')
        entry_id = QuebradoService.registrar(
            quantidade, motivo,
            usuario_id=request.usuario['id'],
            usuario_nome=request.usuario['nome'] or request.usuario['username']
        )
        return jsonify({
            'success': True,
            'id': entry_id,
            'message': f'{quantidade} ovos registrados como quebrados'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/quebrados/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_quebrado(entry_id):
    """Remove um registro de quebrado e devolve ao estoque."""
    try:
        quantidade = QuebradoService.remover(entry_id)
        return jsonify({
            'success': True,
            'message': f'{quantidade} ovos devolvidos ao estoque'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — CONSUMO PESSOAL
# ═══════════════════════════════════════════

@app.route('/api/consumo', methods=['GET'])
@login_required
def get_consumo():
    """Lista registros de consumo pessoal filtrados por mês."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        consumo = ConsumoService.listar(mes)
        return jsonify({'success': True, 'data': consumo})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/consumo', methods=['POST'])
@login_required
def add_consumo():
    """Registra consumo pessoal de ovos."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        quantidade = int(data.get('quantidade', 0))
        observacao = data.get('observacao', '')
        entry_id = ConsumoService.registrar(
            quantidade, observacao,
            usuario_id=request.usuario['id'],
            usuario_nome=request.usuario['nome'] or request.usuario['username']
        )
        return jsonify({
            'success': True,
            'id': entry_id,
            'message': f'{quantidade} ovos registrados como consumo pessoal'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/consumo/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_consumo(entry_id):
    """Remove um registro de consumo e devolve ao estoque."""
    try:
        quantidade = ConsumoService.remover(entry_id)
        return jsonify({
            'success': True,
            'message': f'{quantidade} ovos devolvidos ao estoque'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — DESPESAS
# ═══════════════════════════════════════════

@app.route('/api/despesas', methods=['GET'])
@login_required
def get_despesas():
    """Lista despesas filtradas por mês."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        despesas = DespesaService.listar(mes)
        return jsonify({'success': True, 'data': despesas})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/despesas', methods=['POST'])
@login_required
def add_despesa():
    """Registra uma nova despesa."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        valor = float(data.get('valor', 0))
        descricao = data.get('descricao', '')
        entry_id = DespesaService.registrar(
            valor, descricao,
            usuario_id=request.usuario['id'],
            usuario_nome=request.usuario['nome'] or request.usuario['username']
        )
        return jsonify({
            'success': True,
            'id': entry_id,
            'message': f'Despesa de R$ {valor:.2f} registrada com sucesso'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/despesas/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_despesa(entry_id):
    """Remove uma despesa."""
    try:
        valor = DespesaService.remover(entry_id)
        return jsonify({
            'success': True,
            'message': f'Despesa de R$ {valor:.2f} removida'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — RELATÓRIOS
# ═══════════════════════════════════════════

@app.route('/api/relatorio', methods=['GET'])
@login_required
def get_relatorio():
    """Retorna o resumo mensal."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        resumo = RelatorioService.get_resumo(mes)
        return jsonify({'success': True, 'data': resumo})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/relatorio/anual', methods=['GET'])
@login_required
def get_relatorio_anual():
    """Retorna os dados anuais para gráficos."""
    try:
        ano = request.args.get('ano', datetime.now().strftime('%Y'))
        dados = RelatorioService.get_dados_anuais(ano)
        return jsonify({'success': True, 'data': dados})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/meses', methods=['GET'])
@login_required
def get_meses():
    """Retorna a lista de meses com dados registrados."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT mes_referencia FROM (
                SELECT mes_referencia FROM entradas
                UNION
                SELECT mes_referencia FROM saidas
                UNION
                SELECT mes_referencia FROM quebrados
                UNION
                SELECT mes_referencia FROM consumo
                UNION
                SELECT mes_referencia FROM despesas
            ) AS t ORDER BY mes_referencia DESC
        """)
        meses = [row['mes_referencia'] for row in cursor.fetchall()]
        conn.close()

        # Sempre incluir mês atual
        current = datetime.now().strftime('%Y-%m')
        if current not in meses:
            meses.insert(0, current)

        return jsonify({'success': True, 'data': meses})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — ADMINISTRAÇÃO DE USUÁRIOS
# ═══════════════════════════════════════════

@app.route('/api/admin/usuarios', methods=['GET'])
@admin_required
def admin_listar_usuarios():
    """Lista todos os usuários (apenas admin)."""
    try:
        usuarios = AuthService.listar_usuarios()
        return jsonify({'success': True, 'data': usuarios})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/usuarios', methods=['POST'])
@admin_required
def admin_criar_usuario():
    """Cria um novo usuário (apenas admin)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        usuario = AuthService.criar_usuario(
            username=data.get('username', ''),
            password=data.get('password', ''),
            nome=data.get('nome', ''),
            is_admin=data.get('is_admin', False)
        )
        return jsonify({
            'success': True,
            'data': usuario,
            'message': f'Usuário "{usuario["username"]}" criado com sucesso'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/usuarios/<int:usuario_id>', methods=['PUT'])
@admin_required
def admin_atualizar_usuario(usuario_id):
    """Atualiza um usuário (apenas admin)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        AuthService.atualizar_usuario(
            usuario_id,
            nome=data.get('nome'),
            is_admin=data.get('is_admin'),
            nova_senha=data.get('nova_senha')
        )
        return jsonify({'success': True, 'message': 'Usuário atualizado'})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/usuarios/<int:usuario_id>', methods=['DELETE'])
@admin_required
def admin_deletar_usuario(usuario_id):
    """Remove um usuário (apenas admin)."""
    try:
        AuthService.deletar_usuario(usuario_id)
        return jsonify({'success': True, 'message': 'Usuário removido com sucesso'})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — CONFIGURAÇÕES DO ADMIN
# ═══════════════════════════════════════════

@app.route('/api/admin/configuracoes', methods=['GET'])
@admin_required
def admin_get_configuracoes():
    """Retorna todas as configurações (apenas admin)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chave, valor FROM configuracoes")
        rows = cursor.fetchall()
        conn.close()
        
        config = {row['chave']: row['valor'] for row in rows}
        return jsonify({'success': True, 'data': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/configuracoes', methods=['PUT'])
@admin_required
def admin_update_configuracoes():
    """Atualiza configurações (apenas admin)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        conn = get_connection()
        cursor = conn.cursor()
        
        # Atualizar consumo_habilitado se fornecido
        if 'consumo_habilitado' in data:
            valor = '1' if data['consumo_habilitado'] else '0'
            cursor.execute(
                """INSERT INTO configuracoes (chave, valor, atualizado_em) 
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(chave) DO UPDATE SET valor = ?, atualizado_em = CURRENT_TIMESTAMP""",
                ('consumo_habilitado', valor, valor)
            )
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Configurações atualizadas'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/configuracoes/consumo-habilitado', methods=['GET'])
@login_required
def get_consumo_habilitado():
    """Verifica se o consumo está habilitado (todos os usuários)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = ?", ('consumo_habilitado',))
        row = cursor.fetchone()
        conn.close()
        
        habilitado = row['valor'] == '1' if row else False
        return jsonify({'success': True, 'data': {'habilitado': habilitado}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — EXPORTAÇÃO (PDF / Excel)
# ═══════════════════════════════════════════

@app.route('/api/export/excel', methods=['GET'])
@login_required
def export_excel():
    """Exporta relatório mensal em Excel."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        output = ExportService.exportar_excel(mes)
        filename = f'EggVault_Relatorio_{mes}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/pdf', methods=['GET'])
@login_required
def export_pdf():
    """Exporta relatório mensal em PDF."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        output = ExportService.exportar_pdf(mes)
        filename = f'EggVault_Relatorio_{mes}.pdf'
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/excel-anual', methods=['GET'])
@login_required
def export_excel_anual():
    """Exporta resumo anual em Excel."""
    try:
        ano = request.args.get('ano', datetime.now().strftime('%Y'))
        output = ExportService.exportar_excel_anual(ano)
        filename = f'EggVault_Anual_{ano}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# INICIALIZAÇÃO
# ═══════════════════════════════════════════

if __name__ == '__main__':
    init_db()
    print("🥚 EggVaultiniciado!")
    print("📍 Acesse: http://localhost:5000")
    app.run(debug=True, port=5000)
