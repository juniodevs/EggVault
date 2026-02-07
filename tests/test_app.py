"""
Testes unitários e funcionais para o EggVault.
Cobre os principais cenários de negócio.
"""

import unittest
import json
import sys
import os
import tempfile

# Usar arquivo temporário para o banco de testes
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), 'ovos_test.db')
os.environ['DATABASE_URL'] = ''   # Forçar SQLite nos testes
os.environ['OVOS_DB_PATH'] = TEST_DB_PATH

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import init_db


def _cleanup_db():
    """Remove o arquivo de banco de dados de teste e WAL files."""
    for path in [TEST_DB_PATH, TEST_DB_PATH + '-wal', TEST_DB_PATH + '-shm']:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


class BaseTestCase(unittest.TestCase):
    """Caso de teste base com setup/teardown do banco."""

    def setUp(self):
        """Configura o app de teste e inicializa o banco."""
        _cleanup_db()
        app.config['TESTING'] = True
        self.client = app.test_client()
        init_db()
        # Auto-login como admin — cookie é preservado pelo test client
        self.client.post(
            '/api/auth/login',
            data=json.dumps({'username': 'admin', 'password': 'admin'}),
            content_type='application/json'
        )

    def tearDown(self):
        """Remove o banco de dados entre testes."""
        _cleanup_db()

    def _post_json(self, url, data):
        """Helper para fazer POST com JSON."""
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

    def _create_user(self, username='joao', password='1234', nome='João', is_admin=False):
        """Helper para criar um usuário via API de admin."""
        return self._post_json('/api/admin/usuarios', {
            'username': username,
            'password': password,
            'nome': nome,
            'is_admin': is_admin
        })

    def _login_as(self, client, username, password):
        """Login com um usuário específico em um client."""
        return client.post(
            '/api/auth/login',
            data=json.dumps({'username': username, 'password': password}),
            content_type='application/json'
        )


class TestEstoque(BaseTestCase):
    """Testes para a funcionalidade de Estoque."""

    def test_estoque_inicial_zerado(self):
        """Estoque deve iniciar em zero."""
        res = self.client.get('/api/estoque')
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['quantidade_total'], 0)
        self.assertEqual(data['data']['status'], 'baixo')
        self.assertEqual(data['data']['cor'], 'vermelho')

    def test_estoque_status_baixo(self):
        """Estoque <= 30 deve ser 'baixo' (vermelho)."""
        self._post_json('/api/entradas', {'quantidade': 20})
        res = self.client.get('/api/estoque')
        data = json.loads(res.data)
        self.assertEqual(data['data']['cor'], 'vermelho')

    def test_estoque_status_medio(self):
        """Estoque entre 31 e 100 deve ser 'medio' (amarelo)."""
        self._post_json('/api/entradas', {'quantidade': 50})
        res = self.client.get('/api/estoque')
        data = json.loads(res.data)
        self.assertEqual(data['data']['cor'], 'amarelo')

    def test_estoque_status_alto(self):
        """Estoque > 100 deve ser 'alto' (verde)."""
        self._post_json('/api/entradas', {'quantidade': 150})
        res = self.client.get('/api/estoque')
        data = json.loads(res.data)
        self.assertEqual(data['data']['cor'], 'verde')


class TestEntradas(BaseTestCase):
    """Testes para a funcionalidade de Entradas."""

    def test_registrar_entrada_valida(self):
        """Deve registrar entrada e atualizar estoque."""
        res = self._post_json('/api/entradas', {'quantidade': 100, 'observacao': 'Coleta matinal'})
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('100', data['message'])

        # Verificar estoque atualizado
        res2 = self.client.get('/api/estoque')
        data2 = json.loads(res2.data)
        self.assertEqual(data2['data']['quantidade_total'], 100)

    def test_entrada_quantidade_zero(self):
        """Deve rejeitar entrada com quantidade zero."""
        res = self._post_json('/api/entradas', {'quantidade': 0})
        data = json.loads(res.data)
        self.assertFalse(data['success'])
        self.assertEqual(res.status_code, 400)

    def test_entrada_quantidade_negativa(self):
        """Deve rejeitar entrada com quantidade negativa."""
        res = self._post_json('/api/entradas', {'quantidade': -10})
        data = json.loads(res.data)
        self.assertFalse(data['success'])
        self.assertEqual(res.status_code, 400)

    def test_entrada_sem_dados(self):
        """Deve rejeitar entrada sem dados."""
        res = self.client.post('/api/entradas',
                               data='{}',
                               content_type='application/json')
        data = json.loads(res.data)
        self.assertFalse(data['success'])

    def test_listar_entradas_por_mes(self):
        """Deve listar entradas do mês correto."""
        self._post_json('/api/entradas', {'quantidade': 50})
        self._post_json('/api/entradas', {'quantidade': 30})

        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/entradas?mes={mes}')
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 2)

    def test_entradas_multiplas_atualizam_estoque(self):
        """Múltiplas entradas devem somar no estoque."""
        self._post_json('/api/entradas', {'quantidade': 50})
        self._post_json('/api/entradas', {'quantidade': 70})
        self._post_json('/api/entradas', {'quantidade': 30})

        res = self.client.get('/api/estoque')
        data = json.loads(res.data)
        self.assertEqual(data['data']['quantidade_total'], 150)

    def test_desfazer_entrada(self):
        """Desfazer entrada deve subtrair ovos do estoque."""
        r1 = self._post_json('/api/entradas', {'quantidade': 80})
        d1 = json.loads(r1.data)
        entry_id = d1['id']

        # Verificar estoque aumentou
        est1 = json.loads(self.client.get('/api/estoque').data)
        self.assertEqual(est1['data']['quantidade_total'], 80)

        # Desfazer entrada
        res = self.client.delete(f'/api/entradas/{entry_id}')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Verificar estoque zerado
        est2 = json.loads(self.client.get('/api/estoque').data)
        self.assertEqual(est2['data']['quantidade_total'], 0)

    def test_desfazer_entrada_estoque_insuficiente(self):
        """Desfazer entrada deve falhar se estoque ficaria negativo."""
        # Adicionar 50, vender 30, tentar desfazer entrada de 50
        self._post_json('/api/entradas', {'quantidade': 50})
        self._post_json('/api/precos', {'preco_unitario': 1.00})
        self._post_json('/api/saidas', {'quantidade': 30})

        # Estoque = 20; desfazer entrada de 50 impossível
        res = self.client.get('/api/entradas?mes=' + __import__('datetime').datetime.now().strftime('%Y-%m'))
        entradas = json.loads(res.data)['data']
        entry_id = entradas[0]['id']

        res = self.client.delete(f'/api/entradas/{entry_id}')
        self.assertEqual(res.status_code, 400)

    def test_desfazer_entrada_inexistente(self):
        """Desfazer entrada inexistente deve retornar erro."""
        res = self.client.delete('/api/entradas/99999')
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertFalse(data['success'])


class TestVendas(BaseTestCase):
    """Testes para a funcionalidade de Vendas."""

    def _setup_estoque_e_preco(self, quantidade=200, preco=1.50):
        """Helper para configurar estoque e preço."""
        self._post_json('/api/entradas', {'quantidade': quantidade})
        self._post_json('/api/precos', {'preco_unitario': preco})

    def test_venda_com_estoque_suficiente(self):
        """Deve registrar venda quando há estoque."""
        self._setup_estoque_e_preco(100, 1.50)
        res = self._post_json('/api/saidas', {'quantidade': 30})
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Verificar estoque atualizado
        res2 = self.client.get('/api/estoque')
        data2 = json.loads(res2.data)
        self.assertEqual(data2['data']['quantidade_total'], 70)

    def test_venda_sem_estoque_bloqueia(self):
        """Deve bloquear venda quando estoque é insuficiente."""
        self._post_json('/api/precos', {'preco_unitario': 1.50})
        res = self._post_json('/api/saidas', {'quantidade': 10})
        data = json.loads(res.data)
        self.assertFalse(data['success'])
        self.assertIn('insuficiente', data['error'].lower())
        self.assertEqual(res.status_code, 400)

    def test_venda_maior_que_estoque_bloqueia(self):
        """Deve bloquear venda maior que o estoque."""
        self._setup_estoque_e_preco(50, 1.50)
        res = self._post_json('/api/saidas', {'quantidade': 60})
        data = json.loads(res.data)
        self.assertFalse(data['success'])
        self.assertIn('insuficiente', data['error'].lower())

    def test_venda_sem_preco_ativo_bloqueia(self):
        """Deve bloquear venda quando não há preço ativo."""
        self._post_json('/api/entradas', {'quantidade': 100})
        res = self._post_json('/api/saidas', {'quantidade': 10})
        data = json.loads(res.data)
        self.assertFalse(data['success'])
        self.assertIn('preço', data['error'].lower())

    def test_venda_com_preco_customizado(self):
        """Deve aceitar preço customizado na venda."""
        self._post_json('/api/entradas', {'quantidade': 100})
        self._post_json('/api/precos', {'preco_unitario': 1.00})

        res = self._post_json('/api/saidas', {'quantidade': 20, 'preco_unitario': 2.50})
        data = json.loads(res.data)
        self.assertTrue(data['success'])

    def test_venda_quantidade_invalida(self):
        """Deve rejeitar venda com quantidade inválida."""
        self._setup_estoque_e_preco()
        res = self._post_json('/api/saidas', {'quantidade': -5})
        data = json.loads(res.data)
        self.assertFalse(data['success'])

    def test_desfazer_venda(self):
        """Desfazer venda deve devolver ovos ao estoque."""
        self._setup_estoque_e_preco(100, 1.50)
        # Registrar venda
        r1 = self._post_json('/api/saidas', {'quantidade': 30})
        d1 = json.loads(r1.data)
        sale_id = d1['id']

        # Verificar estoque reduziu
        est1 = json.loads(self.client.get('/api/estoque').data)
        self.assertEqual(est1['data']['quantidade_total'], 70)

        # Desfazer venda
        res = self.client.delete(f'/api/saidas/{sale_id}')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Verificar estoque restaurado
        est2 = json.loads(self.client.get('/api/estoque').data)
        self.assertEqual(est2['data']['quantidade_total'], 100)

    def test_desfazer_venda_inexistente(self):
        """Desfazer venda inexistente deve retornar erro."""
        res = self.client.delete('/api/saidas/99999')
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertFalse(data['success'])


class TestPrecos(BaseTestCase):
    """Testes para a funcionalidade de Preços."""

    def test_definir_preco(self):
        """Deve definir novo preço ativo."""
        res = self._post_json('/api/precos', {'preco_unitario': 2.00})
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        res2 = self.client.get('/api/precos/ativo')
        data2 = json.loads(res2.data)
        self.assertEqual(data2['data']['preco_unitario'], 2.00)

    def test_apenas_um_preco_ativo(self):
        """Deve haver apenas um preço ativo por vez."""
        self._post_json('/api/precos', {'preco_unitario': 1.00})
        self._post_json('/api/precos', {'preco_unitario': 2.00})
        self._post_json('/api/precos', {'preco_unitario': 3.00})

        res = self.client.get('/api/precos')
        data = json.loads(res.data)
        ativos = [p for p in data['data'] if p['ativo']]
        self.assertEqual(len(ativos), 1)
        self.assertEqual(ativos[0]['preco_unitario'], 3.00)

    def test_historico_precos(self):
        """Deve manter histórico completo de preços."""
        self._post_json('/api/precos', {'preco_unitario': 1.00})
        self._post_json('/api/precos', {'preco_unitario': 1.50})
        self._post_json('/api/precos', {'preco_unitario': 2.00})

        res = self.client.get('/api/precos')
        data = json.loads(res.data)
        self.assertEqual(len(data['data']), 3)

    def test_preco_negativo_rejeitado(self):
        """Deve rejeitar preço negativo."""
        res = self._post_json('/api/precos', {'preco_unitario': -1.00})
        data = json.loads(res.data)
        self.assertFalse(data['success'])

    def test_preco_zero_aceito(self):
        """Deve aceitar preço zero (doação)."""
        res = self._post_json('/api/precos', {'preco_unitario': 0})
        data = json.loads(res.data)
        self.assertTrue(data['success'])

    def test_mudanca_preco_reflete_nas_vendas(self):
        """Mudança de preço deve refletir nas novas vendas."""
        self._post_json('/api/entradas', {'quantidade': 200})

        # Primeira venda com preço 1.00
        self._post_json('/api/precos', {'preco_unitario': 1.00})
        self._post_json('/api/saidas', {'quantidade': 10})

        # Segunda venda com preço 2.00
        self._post_json('/api/precos', {'preco_unitario': 2.00})
        self._post_json('/api/saidas', {'quantidade': 10})

        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/saidas?mes={mes}')
        data = json.loads(res.data)

        # Verificar que vendas têm preços diferentes
        precos_vendas = sorted([s['preco_unitario'] for s in data['data']])
        self.assertEqual(precos_vendas, [1.00, 2.00])


class TestRelatorios(BaseTestCase):
    """Testes para a funcionalidade de Relatórios."""

    def test_relatorio_mensal_correto(self):
        """Relatório deve refletir entradas e saídas do mês."""
        self._post_json('/api/entradas', {'quantidade': 200})
        self._post_json('/api/precos', {'preco_unitario': 1.50})
        self._post_json('/api/saidas', {'quantidade': 50})

        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/relatorio?mes={mes}')
        data = json.loads(res.data)

        self.assertTrue(data['success'])
        self.assertEqual(data['data']['total_entradas'], 200)
        self.assertEqual(data['data']['total_saidas'], 50)
        self.assertAlmostEqual(data['data']['faturamento_total'], 75.0)

    def test_relatorio_mes_vazio(self):
        """Relatório de mês sem dados deve retornar zeros."""
        res = self.client.get('/api/relatorio?mes=2020-01')
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['total_entradas'], 0)
        self.assertEqual(data['data']['total_saidas'], 0)
        self.assertEqual(data['data']['faturamento_total'], 0.0)

    def test_relatorio_anual(self):
        """Dados anuais devem ser retornados corretamente."""
        from datetime import datetime
        ano = datetime.now().strftime('%Y')
        res = self.client.get(f'/api/relatorio/anual?ano={ano}')
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIsInstance(data['data'], list)

    def test_relatorio_com_multiplos_precos(self):
        """Relatório deve estar correto mesmo com mudanças de preço."""
        self._post_json('/api/entradas', {'quantidade': 300})

        self._post_json('/api/precos', {'preco_unitario': 1.00})
        self._post_json('/api/saidas', {'quantidade': 100})  # 100.00

        self._post_json('/api/precos', {'preco_unitario': 2.00})
        self._post_json('/api/saidas', {'quantidade': 50})  # 100.00

        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/relatorio?mes={mes}')
        data = json.loads(res.data)

        self.assertEqual(data['data']['total_entradas'], 300)
        self.assertEqual(data['data']['total_saidas'], 150)
        self.assertAlmostEqual(data['data']['faturamento_total'], 200.0)


class TestMeses(BaseTestCase):
    """Testes para o endpoint de meses disponíveis."""

    def test_meses_inclui_mes_atual(self):
        """Lista de meses deve sempre incluir o mês atual."""
        res = self.client.get('/api/meses')
        data = json.loads(res.data)
        from datetime import datetime
        current = datetime.now().strftime('%Y-%m')
        self.assertIn(current, data['data'])


class TestQuebrados(BaseTestCase):
    """Testes para ovos quebrados."""

    def _add_stock(self, qty=100):
        return self.client.post('/api/entradas',
            data=json.dumps({'quantidade': qty}),
            content_type='application/json')

    def test_registrar_quebrado(self):
        """Registrar ovos quebrados deve descontar do estoque."""
        self._add_stock(50)
        res = self.client.post('/api/quebrados',
            data=json.dumps({'quantidade': 10, 'motivo': 'Acidente'}),
            content_type='application/json')
        data = json.loads(res.data)
        self.assertEqual(res.status_code, 200)
        self.assertIn('id', data)
        # Estoque diminuiu
        est = json.loads(self.client.get('/api/estoque').data)
        self.assertEqual(est['data']['quantidade_total'], 40)

    def test_quebrado_sem_estoque(self):
        """Não deve registrar quebra se não há estoque suficiente."""
        self._add_stock(5)
        res = self.client.post('/api/quebrados',
            data=json.dumps({'quantidade': 10}),
            content_type='application/json')
        self.assertEqual(res.status_code, 400)

    def test_quebrado_quantidade_invalida(self):
        """Quantidade <= 0 deve ser rejeitada."""
        res = self.client.post('/api/quebrados',
            data=json.dumps({'quantidade': 0}),
            content_type='application/json')
        self.assertEqual(res.status_code, 400)

    def test_listar_quebrados(self):
        """Deve listar quebrados do mês."""
        self._add_stock(50)
        self.client.post('/api/quebrados',
            data=json.dumps({'quantidade': 3, 'motivo': 'Queda'}),
            content_type='application/json')
        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/quebrados?mes={mes}')
        data = json.loads(res.data)
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['quantidade'], 3)

    def test_desfazer_quebrado(self):
        """Desfazer quebra deve devolver ao estoque."""
        self._add_stock(50)
        # Registrar quebra
        r1 = json.loads(self.client.post('/api/quebrados',
            data=json.dumps({'quantidade': 10}),
            content_type='application/json').data)
        entry_id = r1['id']
        # Desfazer
        res = self.client.delete(f'/api/quebrados/{entry_id}')
        self.assertEqual(res.status_code, 200)
        # Estoque restaurado
        est = json.loads(self.client.get('/api/estoque').data)
        self.assertEqual(est['data']['quantidade_total'], 50)

    def test_relatorio_inclui_quebrados(self):
        """Relatório do mês deve incluir total de quebrados."""
        self._add_stock(100)
        self.client.post('/api/quebrados',
            data=json.dumps({'quantidade': 7}),
            content_type='application/json')
        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/relatorio?mes={mes}')
        data = json.loads(res.data)
        self.assertEqual(data['data']['total_quebrados'], 7)


class TestPaginaPrincipal(BaseTestCase):
    """Testes para a página principal."""

    def test_pagina_carrega(self):
        """Página principal deve carregar com status 200."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'EggVault', res.data)


class TestAutenticacao(BaseTestCase):
    """Testes para o sistema de autenticação."""

    def test_login_valido(self):
        """Login com credenciais corretas deve retornar token."""
        # Novo client sem cookie
        client = app.test_client()
        res = client.post(
            '/api/auth/login',
            data=json.dumps({'username': 'admin', 'password': 'admin'}),
            content_type='application/json'
        )
        data = json.loads(res.data)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('token', data['data'])
        self.assertEqual(data['data']['usuario']['username'], 'admin')

    def test_login_senha_errada(self):
        """Login com senha errada deve ser rejeitado."""
        client = app.test_client()
        res = client.post(
            '/api/auth/login',
            data=json.dumps({'username': 'admin', 'password': 'wrongpassword'}),
            content_type='application/json'
        )
        data = json.loads(res.data)
        self.assertEqual(res.status_code, 401)
        self.assertFalse(data['success'])

    def test_login_usuario_inexistente(self):
        """Login com usuário inexistente deve ser rejeitado."""
        client = app.test_client()
        res = client.post(
            '/api/auth/login',
            data=json.dumps({'username': 'fazendeiro', 'password': 'abc'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 401)

    def test_endpoint_protegido_sem_auth(self):
        """Endpoint protegido sem token deve retornar 401."""
        client = app.test_client()  # Sem login
        res = client.get('/api/estoque')
        data = json.loads(res.data)
        self.assertEqual(res.status_code, 401)
        self.assertFalse(data['success'])
        self.assertTrue(data.get('auth_required'))

    def test_me_retorna_dados_usuario(self):
        """Endpoint /me deve retornar dados do usuário logado."""
        res = self.client.get('/api/auth/me')
        data = json.loads(res.data)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['username'], 'admin')

    def test_logout(self):
        """Logout deve invalidar sessão."""
        res = self.client.post('/api/auth/logout')
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Após logout, me deve falhar
        res2 = self.client.get('/api/auth/me')
        self.assertEqual(res2.status_code, 401)

    def test_alterar_senha(self):
        """Alterar senha deve funcionar com credenciais corretas."""
        res = self._post_json('/api/auth/alterar-senha', {
            'senha_atual': 'admin',
            'nova_senha': 'novasenha123'
        })
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Login com nova senha deve funcionar
        client = app.test_client()
        res2 = client.post(
            '/api/auth/login',
            data=json.dumps({'username': 'admin', 'password': 'novasenha123'}),
            content_type='application/json'
        )
        data2 = json.loads(res2.data)
        self.assertTrue(data2['success'])

    def test_alterar_senha_atual_errada(self):
        """Alterar senha com senha atual errada deve falhar."""
        res = self._post_json('/api/auth/alterar-senha', {
            'senha_atual': 'errada',
            'nova_senha': 'nova123'
        })
        data = json.loads(res.data)
        self.assertEqual(res.status_code, 400)
        self.assertFalse(data['success'])


class TestExportacao(BaseTestCase):
    """Testes para exportação em PDF e Excel."""

    def _setup_dados(self):
        """Cria dados de exemplo para exportação."""
        self._post_json('/api/entradas', {'quantidade': 100, 'observacao': 'Teste'})
        self._post_json('/api/precos', {'preco_unitario': 1.50})
        self._post_json('/api/saidas', {'quantidade': 30})
        self.client.post('/api/quebrados',
            data=json.dumps({'quantidade': 5, 'motivo': 'Teste'}),
            content_type='application/json')

    def test_export_excel_mensal(self):
        """Exportar Excel mensal deve retornar arquivo .xlsx."""
        self._setup_dados()
        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/export/excel?mes={mes}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('spreadsheet', res.content_type)

    def test_export_pdf_mensal(self):
        """Exportar PDF mensal deve retornar arquivo .pdf."""
        self._setup_dados()
        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/export/pdf?mes={mes}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('pdf', res.content_type)

    def test_export_excel_anual(self):
        """Exportar Excel anual deve retornar arquivo .xlsx."""
        self._setup_dados()
        from datetime import datetime
        ano = datetime.now().strftime('%Y')
        res = self.client.get(f'/api/export/excel-anual?ano={ano}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('spreadsheet', res.content_type)

    def test_export_sem_dados(self):
        """Exportar mês sem dados deve funcionar sem erro."""
        res = self.client.get('/api/export/excel?mes=2020-01')
        self.assertEqual(res.status_code, 200)

    def test_export_sem_auth(self):
        """Exportar sem autenticação deve retornar 401."""
        client = app.test_client()
        res = client.get('/api/export/excel')
        self.assertEqual(res.status_code, 401)


class TestAdminUsuarios(BaseTestCase):
    """Testes para o painel de administração de usuários."""

    def test_listar_usuarios(self):
        """Admin deve poder listar todos os usuários."""
        res = self.client.get('/api/admin/usuarios')
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIsInstance(data['data'], list)
        self.assertGreaterEqual(len(data['data']), 1)
        # Verificar que admin está na lista
        usernames = [u['username'] for u in data['data']]
        self.assertIn('admin', usernames)

    def test_criar_usuario(self):
        """Admin deve criar um novo usuário com sucesso."""
        res = self._create_user('maria', '1234', 'Maria Silva')
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['username'], 'maria')
        self.assertFalse(data['data']['is_admin'])

    def test_criar_usuario_admin(self):
        """Admin deve criar outro admin."""
        res = self._create_user('supervisor', 'senha123', 'Supervisor', is_admin=True)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['is_admin'])

    def test_criar_usuario_duplicado(self):
        """Criar usuário com username duplicado deve falhar."""
        self._create_user('joao', '1234', 'João')
        res = self._create_user('joao', '5678', 'João 2')
        data = json.loads(res.data)
        self.assertFalse(data['success'])
        self.assertEqual(res.status_code, 400)

    def test_criar_usuario_dados_invalidos(self):
        """Username curto ou senha curta devem ser rejeitados."""
        # Username muito curto
        res = self._create_user('ab', '1234', 'Teste')
        self.assertEqual(res.status_code, 400)

        # Senha muito curta
        res = self._create_user('teste', '12', 'Teste')
        self.assertEqual(res.status_code, 400)

    def test_deletar_usuario(self):
        """Admin deve poder deletar um usuário."""
        r = self._create_user('temp', '1234', 'Temporário')
        user_id = json.loads(r.data)['data']['id']

        res = self.client.delete(f'/api/admin/usuarios/{user_id}')
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Verificar que foi removido
        lista = json.loads(self.client.get('/api/admin/usuarios').data)
        usernames = [u['username'] for u in lista['data']]
        self.assertNotIn('temp', usernames)

    def test_nao_deletar_ultimo_admin(self):
        """Não deve permitir deletar o último admin."""
        # Buscar ID do admin
        lista = json.loads(self.client.get('/api/admin/usuarios').data)
        admin_id = next(u['id'] for u in lista['data'] if u['username'] == 'admin')

        res = self.client.delete(f'/api/admin/usuarios/{admin_id}')
        data = json.loads(res.data)
        self.assertFalse(data['success'])
        self.assertEqual(res.status_code, 400)

    def test_redefinir_senha_usuario(self):
        """Admin deve poder redefinir senha de outro usuário."""
        self._create_user('pedro', '1234', 'Pedro')

        # Buscar ID
        lista = json.loads(self.client.get('/api/admin/usuarios').data)
        pedro_id = next(u['id'] for u in lista['data'] if u['username'] == 'pedro')

        # Redefinir senha
        res = self.client.put(
            f'/api/admin/usuarios/{pedro_id}',
            data=json.dumps({'nova_senha': 'novasenha'}),
            content_type='application/json'
        )
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Login com nova senha deve funcionar
        client2 = app.test_client()
        res2 = self._login_as(client2, 'pedro', 'novasenha')
        self.assertEqual(res2.status_code, 200)

    def test_non_admin_nao_acessa_painel(self):
        """Usuário não-admin deve receber 403 no painel admin."""
        self._create_user('trabalhador', '1234', 'Trabalhador')

        client2 = app.test_client()
        self._login_as(client2, 'trabalhador', '1234')

        res = client2.get('/api/admin/usuarios')
        self.assertEqual(res.status_code, 403)

    def test_non_admin_nao_cria_usuario(self):
        """Usuário não-admin não deve poder criar contas."""
        self._create_user('trabalhador', '1234', 'Trabalhador')

        client2 = app.test_client()
        self._login_as(client2, 'trabalhador', '1234')

        res = client2.post(
            '/api/admin/usuarios',
            data=json.dumps({'username': 'hacker', 'password': '1234', 'nome': 'Hacker'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 403)


class TestMultiConta(BaseTestCase):
    """Testes para funcionalidade multi-conta (logs com nome do usuário)."""

    def test_entrada_registra_nome_usuario(self):
        """Entrada deve registrar qual usuário fez a ação."""
        # Admin registra entrada
        self._post_json('/api/entradas', {'quantidade': 50})

        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/entradas?mes={mes}')
        data = json.loads(res.data)

        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['usuario_nome'], 'Administrador')

    def test_venda_registra_nome_usuario(self):
        """Venda deve registrar qual usuário fez a ação."""
        self._post_json('/api/entradas', {'quantidade': 100})
        self._post_json('/api/precos', {'preco_unitario': 1.50})
        self._post_json('/api/saidas', {'quantidade': 20})

        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/saidas?mes={mes}')
        data = json.loads(res.data)

        self.assertEqual(data['data'][0]['usuario_nome'], 'Administrador')

    def test_quebrado_registra_nome_usuario(self):
        """Quebra deve registrar qual usuário fez a ação."""
        self._post_json('/api/entradas', {'quantidade': 50})
        self.client.post('/api/quebrados',
            data=json.dumps({'quantidade': 5, 'motivo': 'Teste'}),
            content_type='application/json')

        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/quebrados?mes={mes}')
        data = json.loads(res.data)

        self.assertEqual(data['data'][0]['usuario_nome'], 'Administrador')

    def test_diferentes_usuarios_nos_logs(self):
        """Ações de diferentes usuários devem aparecer nos logs."""
        # Admin adiciona estoque
        self._post_json('/api/entradas', {'quantidade': 100})

        # Criar segundo usuário
        self._create_user('maria', '1234', 'Maria Silva')

        # Maria faz login
        client2 = app.test_client()
        self._login_as(client2, 'maria', '1234')

        # Maria registra entrada
        client2.post('/api/entradas',
            data=json.dumps({'quantidade': 30, 'observacao': 'Maria coletou'}),
            content_type='application/json')

        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res = self.client.get(f'/api/entradas?mes={mes}')
        data = json.loads(res.data)

        nomes = [e['usuario_nome'] for e in data['data']]
        self.assertIn('Administrador', nomes)
        self.assertIn('Maria Silva', nomes)

    def test_usuario_normal_faz_venda(self):
        """Usuário não-admin deve poder registrar vendas normalmente."""
        # Admin prepara estoque e preço
        self._post_json('/api/entradas', {'quantidade': 100})
        self._post_json('/api/precos', {'preco_unitario': 2.00})

        # Criar usuário normal
        self._create_user('carlos', '1234', 'Carlos')

        # Carlos faz login e vende
        client2 = app.test_client()
        self._login_as(client2, 'carlos', '1234')

        res = client2.post('/api/saidas',
            data=json.dumps({'quantidade': 10}),
            content_type='application/json')
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Verificar no log
        from datetime import datetime
        mes = datetime.now().strftime('%Y-%m')
        res2 = self.client.get(f'/api/saidas?mes={mes}')
        vendas = json.loads(res2.data)['data']
        self.assertEqual(vendas[0]['usuario_nome'], 'Carlos')


if __name__ == '__main__':
    unittest.main(verbosity=2)
