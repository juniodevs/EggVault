"""
Testes E2E — Gestão de Clientes.

Cobre:
  • Aba Clientes visível na sidebar
  • Cadastro de novo cliente (com e sem número)
  • Busca/filtro de clientes na tabela
  • Edição de cliente via modal
  • Remoção de cliente com confirmação
  • Exibição de badge de inatividade
  • Botão WhatsApp habilitado/desabilitado
  • Select de cliente no formulário de venda
  • Vinculação de cliente a venda
"""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.ui]


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _go_clientes(page):
    """Navega para a aba Clientes e aguarda carregamento."""
    page.click('li[data-tab="clientes"]')
    page.wait_for_timeout(800)


def _cadastrar_cliente(page, nome, numero=''):
    """Preenche e submete o formulário de novo cliente."""
    page.fill('#cliente-nome', nome)
    if numero:
        page.fill('#cliente-numero', numero)
    page.click('#form-cliente button[type="submit"]')
    page.wait_for_timeout(1200)


def _add_stock(page, qty=100):
    """Helper: adiciona estoque via aba Entradas."""
    page.click('li[data-tab="entradas"]')
    page.wait_for_timeout(500)
    page.fill('#entrada-quantidade', str(qty))
    page.click('#form-entrada button[type="submit"]')
    page.wait_for_timeout(1500)


# ────────────────────────────────────────────────────────────────────────────
# Navegação
# ────────────────────────────────────────────────────────────────────────────

class TestClientesNavegacao:
    """Testa presença e acessibilidade da aba Clientes."""

    def test_aba_clientes_visivel_na_sidebar(self, authenticated_page):
        """A aba Clientes deve aparecer na sidebar."""
        page = authenticated_page
        nav_item = page.locator('li[data-tab="clientes"]')
        assert nav_item.is_visible()

    def test_click_aba_clientes_exibe_secao(self, authenticated_page):
        """Clicar em Clientes deve exibir a seção correta."""
        page = authenticated_page
        _go_clientes(page)

        section = page.locator('#tab-clientes')
        assert section.is_visible()

    def test_formulario_cadastro_visivel(self, authenticated_page):
        """Formulário de cadastro deve estar visível na aba."""
        page = authenticated_page
        _go_clientes(page)

        assert page.locator('#form-cliente').is_visible()
        assert page.locator('#cliente-nome').is_visible()
        assert page.locator('#cliente-numero').is_visible()

    def test_tabela_clientes_visivel(self, authenticated_page):
        """Tabela de clientes deve estar visível."""
        page = authenticated_page
        _go_clientes(page)

        assert page.locator('#clientes-list').is_visible()

    def test_campo_busca_visivel(self, authenticated_page):
        """Campo de busca deve estar visível."""
        page = authenticated_page
        _go_clientes(page)

        assert page.locator('#clientes-search').is_visible()


# ────────────────────────────────────────────────────────────────────────────
# Cadastro
# ────────────────────────────────────────────────────────────────────────────

class TestClientesCadastro:
    """Testa o formulário de cadastro de clientes."""

    def test_cadastrar_cliente_com_nome_e_numero(self, authenticated_page):
        """Deve cadastrar cliente com nome e número."""
        page = authenticated_page
        _go_clientes(page)

        _cadastrar_cliente(page, 'Maria da Silva', '11999990000')

        toast = page.locator('#toast-container .toast, #toast-container div')
        toast.first.wait_for(state='visible', timeout=5000)

        table_text = page.locator('#clientes-list').inner_text()
        assert 'Maria da Silva' in table_text

    def test_cadastrar_cliente_sem_numero(self, authenticated_page):
        """Deve cadastrar cliente apenas com nome."""
        page = authenticated_page
        _go_clientes(page)

        _cadastrar_cliente(page, 'João Sem Número')

        table_text = page.locator('#clientes-list').inner_text()
        assert 'João Sem Número' in table_text

    def test_cadastrar_cliente_nome_vazio_falha(self, authenticated_page):
        """Submit com nome vazio não deve criar novo registro na tabela."""
        page = authenticated_page
        _go_clientes(page)

        # Contar linhas antes da tentativa
        rows_before = page.locator('#clientes-list tr').count()

        # Tentar submeter sem nome (campo obrigatório — HTML5 required)
        page.fill('#cliente-nome', '')
        page.evaluate("document.querySelector('#form-cliente button[type=submit]').click()")
        page.wait_for_timeout(800)

        # Nenhuma linha nova deve ter sido adicionada
        rows_after = page.locator('#clientes-list tr').count()
        assert rows_after == rows_before

    def test_form_limpo_apos_cadastro(self, authenticated_page):
        """Formulário deve ser limpo após cadastro bem-sucedido."""
        page = authenticated_page
        _go_clientes(page)

        _cadastrar_cliente(page, 'Teste Limpeza', '11988880000')

        # Campo nome deve estar vazio
        nome_val = page.locator('#cliente-nome').input_value()
        assert nome_val == ''

    def test_multiplos_clientes_aparecem_na_tabela(self, authenticated_page):
        """Múltiplos clientes devem aparecer na tabela."""
        page = authenticated_page
        _go_clientes(page)

        _cadastrar_cliente(page, 'Cliente A', '11900000001')
        _cadastrar_cliente(page, 'Cliente B', '11900000002')
        _cadastrar_cliente(page, 'Cliente C', '11900000003')

        table_text = page.locator('#clientes-list').inner_text()
        assert 'Cliente A' in table_text
        assert 'Cliente B' in table_text
        assert 'Cliente C' in table_text


# ────────────────────────────────────────────────────────────────────────────
# Busca / Filtro
# ────────────────────────────────────────────────────────────────────────────

class TestClientesBusca:
    """Testa o campo de busca."""

    def test_busca_por_nome_filtra_resultados(self, authenticated_page):
        """Busca por nome deve filtrar a tabela."""
        page = authenticated_page
        _go_clientes(page)

        _cadastrar_cliente(page, 'Ana Carolina')
        _cadastrar_cliente(page, 'Bruno Alves', '11922220000')

        page.fill('#clientes-search', 'Ana')
        page.wait_for_timeout(400)

        table_text = page.locator('#clientes-list').inner_text()
        assert 'Ana Carolina' in table_text
        assert 'Bruno' not in table_text

    def test_busca_vazia_exibe_todos(self, authenticated_page):
        """Limpar busca deve exibir todos os clientes."""
        page = authenticated_page
        _go_clientes(page)

        _cadastrar_cliente(page, 'Alice')
        _cadastrar_cliente(page, 'Bob', '11933330000')

        # Filtrar
        page.fill('#clientes-search', 'Alice')
        page.wait_for_timeout(300)

        # Limpar
        page.fill('#clientes-search', '')
        page.wait_for_timeout(300)

        table_text = page.locator('#clientes-list').inner_text()
        assert 'Alice' in table_text
        assert 'Bob' in table_text


# ────────────────────────────────────────────────────────────────────────────
# Inatividade
# ────────────────────────────────────────────────────────────────────────────

class TestClientesInatividade:
    """Testa a exibição de badges de inatividade."""

    def test_cliente_novo_exibe_nunca_comprou(self, authenticated_page):
        """Cliente recém-criado deve exibir 'Nunca comprou'."""
        page = authenticated_page
        _go_clientes(page)

        _cadastrar_cliente(page, 'Novo Cliente Teste')

        table_text = page.locator('#clientes-list').inner_text()
        assert 'Nunca comprou' in table_text


# ────────────────────────────────────────────────────────────────────────────
# WhatsApp
# ────────────────────────────────────────────────────────────────────────────

class TestClientesWhatsApp:
    """Testa o botão de WhatsApp."""

    def test_cliente_com_numero_tem_botao_wa_habilitado(self, authenticated_page):
        """Cliente com número deve ter botão WhatsApp clicável."""
        page = authenticated_page
        _go_clientes(page)

        nome = 'WA Teste Unico'
        _cadastrar_cliente(page, nome, '11999990000')

        row = page.locator('#clientes-list tr', has=page.locator('text=' + nome)).first
        wa_btn = row.locator('a.btn-whatsapp')
        assert wa_btn.is_visible()
        assert wa_btn.is_enabled()

    def test_cliente_sem_numero_tem_botao_wa_desabilitado(self, authenticated_page):
        """Cliente sem número deve ter botão WhatsApp desabilitado."""
        page = authenticated_page
        _go_clientes(page)

        nome = 'Sem Numero WA Unico'
        _cadastrar_cliente(page, nome)

        row = page.locator('#clientes-list tr', has=page.locator('text=' + nome)).first
        wa_btn = row.locator('button.btn-whatsapp[disabled]')
        assert wa_btn.is_visible()

    def test_whatsapp_url_prefixo_brasil(self, authenticated_page):
        """Número sem DDI deve ter URL com prefixo 55."""
        page = authenticated_page
        _go_clientes(page)

        nome = 'Brasil DDI Unico'
        _cadastrar_cliente(page, nome, '11987650000')

        # Localizar a linha específica deste cliente
        row = page.locator('#clientes-list tr', has=page.locator('text=' + nome)).first
        wa_link = row.locator('a.btn-whatsapp')
        href = wa_link.get_attribute('href')
        assert 'wa.me/5511987650000' in href


# ────────────────────────────────────────────────────────────────────────────
# Edição
# ────────────────────────────────────────────────────────────────────────────

class TestClientesEdicao:
    """Testa o modal de edição."""

    def test_botao_editar_abre_modal(self, authenticated_page):
        """Botão de editar deve abrir o modal."""
        page = authenticated_page
        _go_clientes(page)

        nome = 'Para Editar Unico'
        _cadastrar_cliente(page, nome, '11900000005')

        row = page.locator('#clientes-list tr', has=page.locator('text=' + nome)).first
        row.locator('.btn-edit-small').click()
        page.wait_for_timeout(500)

        modal = page.locator('#modal-editar-cliente')
        assert modal.is_visible()

    def test_modal_preenchido_com_dados_do_cliente(self, authenticated_page):
        """Modal de edição deve vir preenchido com os dados atuais."""
        page = authenticated_page
        _go_clientes(page)

        nome = 'Dados Preenchidos Unico'
        _cadastrar_cliente(page, nome, '11900000006')

        # Clicar no botão editar da linha específica deste cliente
        row = page.locator('#clientes-list tr', has=page.locator('text=' + nome)).first
        row.locator('.btn-edit-small').click()
        page.wait_for_timeout(500)

        nome_val = page.locator('#editar-cliente-nome').input_value()
        assert nome in nome_val

    def test_cancelar_modal_fecha_sem_salvar(self, authenticated_page):
        """Cancelar no modal deve fechar sem alterar dados."""
        page = authenticated_page
        _go_clientes(page)

        nome = 'Cancelar Teste Unico'
        _cadastrar_cliente(page, nome, '11900000007')

        row = page.locator('#clientes-list tr', has=page.locator('text=' + nome)).first
        row.locator('.btn-edit-small').click()
        page.wait_for_timeout(500)

        page.fill('#editar-cliente-nome', 'Nome Modificado')
        page.click('button[onclick="hideEditarCliente()"]')
        page.wait_for_timeout(500)

        # Modal fechado
        modal = page.locator('#modal-editar-cliente')
        assert not modal.is_visible()

        # Dados originais preservados
        table_text = page.locator('#clientes-list').inner_text()
        assert nome in table_text

    def test_salvar_edicao_atualiza_tabela(self, authenticated_page):
        """Salvar edição deve atualizar o nome na tabela."""
        page = authenticated_page
        _go_clientes(page)

        nome = 'Original Nome Unico'
        _cadastrar_cliente(page, nome, '11900000008')

        row = page.locator('#clientes-list tr', has=page.locator('text=' + nome)).first
        row.locator('.btn-edit-small').click()
        page.wait_for_timeout(500)

        page.fill('#editar-cliente-nome', 'Nome Atualizado Unico')
        page.click('#form-editar-cliente button[type="submit"]')
        page.wait_for_timeout(1500)

        table_text = page.locator('#clientes-list').inner_text()
        assert 'Nome Atualizado Unico' in table_text


# ────────────────────────────────────────────────────────────────────────────
# Remoção
# ────────────────────────────────────────────────────────────────────────────

class TestClientesRemocao:
    """Testa a exclusão de clientes."""

    def test_remover_cliente_com_confirmacao(self, authenticated_page):
        """Deve remover cliente ao confirmar a exclusão."""
        page = authenticated_page
        _go_clientes(page)

        nome = 'Para Deletar Unico'
        _cadastrar_cliente(page, nome, '11900000009')

        # Localizar a linha específica e clicar em remover
        row = page.locator('#clientes-list tr', has=page.locator('text=' + nome)).first
        row.locator('.btn-undo').click()
        page.wait_for_timeout(500)

        # Confirmar no dialog customizado
        confirm_btn = page.locator('#confirm-ok-btn')
        confirm_btn.wait_for(state='visible', timeout=3000)
        confirm_btn.click()
        page.wait_for_timeout(1500)

        table_text = page.locator('#clientes-list').inner_text()
        assert nome not in table_text

    def test_cancelar_remocao_preserva_cliente(self, authenticated_page):
        """Cancelar exclusão deve manter o cliente na lista."""
        page = authenticated_page
        _go_clientes(page)

        nome = 'Nao Deletar Unico'
        _cadastrar_cliente(page, nome, '11900000010')

        row = page.locator('#clientes-list tr', has=page.locator('text=' + nome)).first
        row.locator('.btn-undo').click()
        page.wait_for_timeout(500)

        cancel_btn = page.locator('#confirm-cancel-btn')
        cancel_btn.wait_for(state='visible', timeout=3000)
        cancel_btn.click()
        page.wait_for_timeout(600)

        table_text = page.locator('#clientes-list').inner_text()
        assert nome in table_text


# ────────────────────────────────────────────────────────────────────────────
# Integração com Vendas
# ────────────────────────────────────────────────────────────────────────────

class TestClientesIntegracaoVendas:
    """Testa a integração entre clientes e vendas."""

    def test_select_cliente_visivel_no_form_venda(self, authenticated_page):
        """Select de cliente deve aparecer no formulário de vendas."""
        page = authenticated_page
        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(800)

        select = page.locator('#venda-cliente')
        assert select.is_visible()

    def test_cliente_aparece_no_select_de_venda(self, authenticated_page):
        """Cliente cadastrado deve aparecer no select do formulário de vendas."""
        page = authenticated_page

        # Cadastrar cliente primeiro
        _go_clientes(page)
        _cadastrar_cliente(page, 'Cliente Venda Teste', '11999990001')

        # Ir para vendas
        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(1200)

        select_text = page.locator('#venda-cliente').inner_text()
        assert 'Cliente Venda Teste' in select_text

    def test_registrar_venda_com_cliente_selecionado(self, authenticated_page):
        """Deve registrar venda vinculada a um cliente."""
        page = authenticated_page
        _add_stock(page, 100)

        # Cadastrar cliente
        _go_clientes(page)
        _cadastrar_cliente(page, 'Comprador VIP', '11999990002')

        # Ir para vendas
        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(1200)

        page.fill('#venda-quantidade', '10')
        page.fill('#venda-preco', '1.50')

        # Selecionar cliente
        page.select_option('#venda-cliente', label='Comprador VIP')
        page.wait_for_timeout(200)

        page.click('#form-venda button[type="submit"]')

        toast = page.locator('#toast-container .toast, #toast-container div')
        toast.first.wait_for(state='visible', timeout=8000)

        # Verificar que o nome do cliente aparece na tabela de vendas
        page.wait_for_timeout(1000)
        vendas_text = page.locator('#vendas-hoje-list').inner_text()
        assert 'Comprador VIP' in vendas_text

    def test_select_cliente_zerado_apos_venda(self, authenticated_page):
        """Select de cliente deve ser resetado após registrar a venda."""
        page = authenticated_page
        _add_stock(page, 50)

        _go_clientes(page)
        _cadastrar_cliente(page, 'Reset Teste', '11999990003')

        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(1200)

        page.fill('#venda-quantidade', '5')
        page.fill('#venda-preco', '1.00')
        page.select_option('#venda-cliente', label='Reset Teste')
        page.click('#form-venda button[type="submit"]')
        page.wait_for_timeout(1500)

        # Select deve voltar ao placeholder
        selected_val = page.locator('#venda-cliente').input_value()
        assert selected_val == '' or selected_val == '0'

    def test_venda_sem_cliente_continua_funcionando(self, authenticated_page):
        """Registrar venda sem selecionar cliente deve funcionar normalmente."""
        page = authenticated_page
        _add_stock(page, 50)

        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(800)

        page.fill('#venda-quantidade', '5')
        page.fill('#venda-preco', '1.00')
        # NÃO selecionar cliente

        page.click('#form-venda button[type="submit"]')

        toast = page.locator('#toast-container .toast, #toast-container div')
        toast.first.wait_for(state='visible', timeout=8000)

        page.wait_for_timeout(800)
        vendas_text = page.locator('#vendas-hoje-list').inner_text()
        assert '5' in vendas_text
