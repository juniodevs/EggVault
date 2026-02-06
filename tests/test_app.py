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


if __name__ == '__main__':
    unittest.main(verbosity=2)
