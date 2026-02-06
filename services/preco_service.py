"""Serviço de negócios para Preços."""

from repositories.preco_repo import PrecoRepository


class PrecoService:
    """Lógica de negócios para gerenciamento de preços."""

    @staticmethod
    def definir_preco(preco_unitario):
        """
        Define um novo preço ativo (desativa os anteriores).

        Args:
            preco_unitario: Valor do preço (número não negativo).

        Returns:
            ID do preço criado.

        Raises:
            ValueError: Se o valor for inválido.
        """
        if not isinstance(preco_unitario, (int, float)) or preco_unitario < 0:
            raise ValueError("Preço deve ser um número não negativo")
        return PrecoRepository.create(preco_unitario)

    @staticmethod
    def get_ativo():
        """Retorna o preço ativo atual ou None."""
        return PrecoRepository.get_active()

    @staticmethod
    def historico():
        """Retorna todo o histórico de preços."""
        return PrecoRepository.get_all()
