"""Serviço de negócios para Clientes."""

import re
from datetime import datetime, date
from repositories.cliente_repo import ClienteRepository


def _sanitize_numero(numero):
    """Remove espaços, traços e caracteres especiais do número, deixando apenas dígitos e +."""
    if not numero:
        return None
    sanitized = re.sub(r'[^\d+]', '', str(numero).strip())
    return sanitized if sanitized else None


def _calcular_inatividade(data_ultima_compra):
    """
    Calcula quantos dias fazem desde a última compra.

    Retorna:
        dict com 'dias' (int ou None) e 'texto' (str)
    """
    if not data_ultima_compra:
        return {'dias': None, 'texto': 'Nunca comprou'}

    try:
        if isinstance(data_ultima_compra, str):
            # Remover timezone info para compatibilidade
            dt_str = data_ultima_compra.replace('Z', '').split('+')[0]
            if 'T' in dt_str:
                dt = datetime.fromisoformat(dt_str).date()
            else:
                dt = date.fromisoformat(dt_str[:10])
        elif isinstance(data_ultima_compra, datetime):
            dt = data_ultima_compra.date()
        elif isinstance(data_ultima_compra, date):
            dt = data_ultima_compra
        else:
            return {'dias': None, 'texto': 'Nunca comprou'}

        hoje = date.today()
        dias = (hoje - dt).days

        if dias == 0:
            texto = 'Comprou hoje'
        elif dias == 1:
            texto = '1 dia sem comprar'
        else:
            texto = f'{dias} dias sem comprar'

        return {'dias': dias, 'texto': texto}
    except Exception:
        return {'dias': None, 'texto': 'Data inválida'}


def _build_whatsapp_url(numero):
    """
    Constrói URL do WhatsApp a partir do número.
    Se começar com código de país (ex: 55), usa direto.
    Caso contrário, assume Brasil (+55).
    """
    if not numero:
        return None
    digits = re.sub(r'\D', '', numero)
    if not digits:
        return None
    # Número explicitamente com + (já tem código de país)
    if numero.startswith('+'):
        return f'https://wa.me/{digits}'
    # 12+ dígitos sem + → já inclui código de país (ex: 5511999990000)
    if len(digits) >= 12:
        return f'https://wa.me/{digits}'
    # Assume Brasil (+55): DDD + 8/9 dígitos = 10/11 dígitos
    return f'https://wa.me/55{digits}'


class ClienteService:
    """Lógica de negócios para gestão de clientes."""

    @staticmethod
    def criar(nome, numero=None):
        """
        Cria um novo cliente.

        Args:
            nome: Nome do cliente (obrigatório).
            numero: Número de telefone (opcional).

        Returns:
            ID do cliente criado.

        Raises:
            ValueError: Se nome inválido ou cliente duplicado.
        """
        nome = (nome or '').strip()
        if not nome:
            raise ValueError("Nome do cliente é obrigatório")
        if len(nome) > 100:
            raise ValueError("Nome deve ter no máximo 100 caracteres")

        numero = _sanitize_numero(numero)

        # Verificar duplicidade
        if ClienteRepository.exists_by_nome_numero(nome, numero):
            raise ValueError(f'Já existe um cliente com o nome "{nome}" e o mesmo número')

        return ClienteRepository.create(nome, numero)

    @staticmethod
    def listar():
        """Retorna todos os clientes com info de inatividade e link WhatsApp."""
        clientes = ClienteRepository.get_all()
        for c in clientes:
            inatividade = _calcular_inatividade(c.get('data_ultima_compra'))
            c['inatividade_dias'] = inatividade['dias']
            c['inatividade_texto'] = inatividade['texto']
            c['inativo_30d'] = (
                inatividade['dias'] is not None and inatividade['dias'] > 30
            ) or (
                inatividade['dias'] is None  # nunca comprou → também sinalizar
            )
            c['whatsapp_url'] = _build_whatsapp_url(c.get('numero'))
        return clientes

    @staticmethod
    def listar_simples():
        """Retorna lista simplificada (id + nome) para selects."""
        clientes = ClienteRepository.get_all()
        return [{'id': c['id'], 'nome': c['nome']} for c in clientes]

    @staticmethod
    def atualizar(cliente_id, nome=None, numero=None):
        """
        Atualiza dados de um cliente.

        Args:
            cliente_id: ID do cliente.
            nome: Novo nome (opcional).
            numero: Novo número (opcional, passar '' para limpar).

        Raises:
            ValueError: Se cliente não encontrado ou nome inválido.
        """
        cliente = ClienteRepository.get_by_id(cliente_id)
        if not cliente:
            raise ValueError("Cliente não encontrado")

        if nome is not None:
            nome = nome.strip()
            if not nome:
                raise ValueError("Nome do cliente não pode ser vazio")
            if len(nome) > 100:
                raise ValueError("Nome deve ter no máximo 100 caracteres")

        if numero is not None:
            numero = _sanitize_numero(numero)

        # Verificar duplicidade (excluindo o próprio cliente)
        check_nome = nome if nome is not None else cliente['nome']
        check_numero = numero if numero is not None else cliente['numero']
        if ClienteRepository.exists_by_nome_numero(check_nome, check_numero, exclude_id=cliente_id):
            raise ValueError(f'Já existe outro cliente com o nome "{check_nome}" e o mesmo número')

        ClienteRepository.update(cliente_id, nome=nome, numero=numero)

    @staticmethod
    def remover(cliente_id):
        """
        Remove um cliente.

        Raises:
            ValueError: Se cliente não encontrado.
        """
        ClienteRepository.delete(cliente_id)

    @staticmethod
    def registrar_compra(cliente_id):
        """
        Atualiza a data da última compra do cliente para agora.

        Args:
            cliente_id: ID do cliente.
        """
        if not cliente_id:
            return
        cliente = ClienteRepository.get_by_id(cliente_id)
        if not cliente:
            return  # Silencioso — não quebrar o fluxo de venda
        ClienteRepository.update_ultima_compra(cliente_id)
