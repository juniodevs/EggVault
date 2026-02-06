"""
🥚 Egg Manager — Aplicativo de Gerenciamento de Ovos
Servidor Flask com API REST e interface web SPA.
"""

from flask import Flask, render_template, request, jsonify
from database import init_db, get_connection
from services.estoque_service import EstoqueService
from services.entrada_service import EntradaService
from services.saida_service import SaidaService
from services.preco_service import PrecoService
from services.relatorio_service import RelatorioService
from services.quebrado_service import QuebradoService
from datetime import datetime

app = Flask(__name__)


# ═══════════════════════════════════════════
# PÁGINA PRINCIPAL
# ═══════════════════════════════════════════

@app.route('/')
def index():
    """Serve a página principal (SPA)."""
    return render_template('index.html')


# ═══════════════════════════════════════════
# API — ESTOQUE
# ═══════════════════════════════════════════

@app.route('/api/estoque', methods=['GET'])
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
def get_entradas():
    """Lista entradas filtradas por mês."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        entradas = EntradaService.listar(mes)
        return jsonify({'success': True, 'data': entradas})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/entradas', methods=['POST'])
def add_entrada():
    """Registra uma nova entrada de ovos."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        quantidade = int(data.get('quantidade', 0))
        observacao = data.get('observacao', '')
        entry_id = EntradaService.registrar(quantidade, observacao)
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
# API — SAÍDAS / VENDAS
# ═══════════════════════════════════════════

@app.route('/api/saidas', methods=['GET'])
def get_saidas():
    """Lista vendas filtradas por mês."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        saidas = SaidaService.listar(mes)
        return jsonify({'success': True, 'data': saidas})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/saidas', methods=['POST'])
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

        sale_id = SaidaService.registrar(quantidade, preco_unitario)
        return jsonify({
            'success': True,
            'id': sale_id,
            'message': f'{quantidade} ovos vendidos com sucesso'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════
# API — PREÇOS
# ═══════════════════════════════════════════

@app.route('/api/precos', methods=['GET'])
def get_precos():
    """Retorna o histórico de preços."""
    try:
        precos = PrecoService.historico()
        return jsonify({'success': True, 'data': precos})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/precos/ativo', methods=['GET'])
def get_preco_ativo():
    """Retorna o preço ativo atual."""
    try:
        preco = PrecoService.get_ativo()
        return jsonify({'success': True, 'data': preco})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/precos', methods=['POST'])
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
def get_quebrados():
    """Lista registros de ovos quebrados filtrados por mês."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        quebrados = QuebradoService.listar(mes)
        return jsonify({'success': True, 'data': quebrados})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/quebrados', methods=['POST'])
def add_quebrado():
    """Registra ovos quebrados (perda)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        quantidade = int(data.get('quantidade', 0))
        motivo = data.get('motivo', '')
        entry_id = QuebradoService.registrar(quantidade, motivo)
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
# API — RELATÓRIOS
# ═══════════════════════════════════════════

@app.route('/api/relatorio', methods=['GET'])
def get_relatorio():
    """Retorna o resumo mensal."""
    try:
        mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
        resumo = RelatorioService.get_resumo(mes)
        return jsonify({'success': True, 'data': resumo})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/relatorio/anual', methods=['GET'])
def get_relatorio_anual():
    """Retorna os dados anuais para gráficos."""
    try:
        ano = request.args.get('ano', datetime.now().strftime('%Y'))
        dados = RelatorioService.get_dados_anuais(ano)
        return jsonify({'success': True, 'data': dados})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/meses', methods=['GET'])
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
            ) ORDER BY mes_referencia DESC
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
# INICIALIZAÇÃO
# ═══════════════════════════════════════════

if __name__ == '__main__':
    init_db()
    print("🥚 Egg Manager iniciado!")
    print("📍 Acesse: http://localhost:5000")
    app.run(debug=True, port=5000)
