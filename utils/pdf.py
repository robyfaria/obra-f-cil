"""
Módulo de geração de PDF para orçamentos
Usa fpdf2 para gerar PDFs simples e legíveis
"""

from fpdf import FPDF
from datetime import datetime
from pathlib import Path
from typing import Optional

LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "logo.png"


class OrcamentoPDF(FPDF):
    """Classe customizada para gerar PDF de orçamentos"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.logo_path = LOGO_PATH if LOGO_PATH.exists() else None
        
    def header(self):
        """Cabeçalho do PDF"""
        if self.logo_path:
            self.image(str(self.logo_path), x=10, y=8, w=18)
            self.set_y(10)
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(26, 82, 118)  # Azul escuro
        self.cell(0, 10, 'ORÇAMENTO DE PINTURA', ln=True, align='C')
        self.ln(5)
        
    def footer(self):
        """Rodapé do PDF"""
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', align='C')


def formatar_moeda(valor: float) -> str:
    """Formata valor para moeda brasileira"""
    if valor is None:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def normalizar_texto(valor: Optional[object], padrao: str = "-") -> str:
    """Normaliza valores para texto no PDF."""
    if valor is None:
        return padrao
    return str(valor)


def quebrar_texto_em_linhas(pdf: FPDF, texto: str, largura_max: float) -> list[str]:
    """Divide um texto em linhas que caibam na largura informada."""
    palavras = texto.split()
    if not palavras:
        return [""]

    linhas = []
    linha_atual = ""
    for palavra in palavras:
        teste = f"{linha_atual} {palavra}".strip()
        if pdf.get_string_width(teste) <= largura_max:
            linha_atual = teste
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra

    if linha_atual:
        linhas.append(linha_atual)

    return linhas


def gerar_pdf_orcamento(orcamento: dict, fases: list, servicos_por_fase: dict) -> bytes:
    """
    Gera o PDF de um orçamento
    
    Args:
        orcamento: Dados do orçamento com obra e cliente
        fases: Lista de fases do orçamento
        servicos_por_fase: Dict com fase_id -> lista de serviços
        
    Returns:
        bytes: Conteúdo do PDF
    """
    pdf = OrcamentoPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Dados do cliente e obra
    obra = orcamento.get('obras', {})
    cliente = obra.get('clientes', {})
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    
    # Box de informações
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, 'INFORMAÇÕES DO CLIENTE', ln=True, fill=True)
    
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(30, 7, 'Cliente:', ln=False)
    pdf.cell(0, 7, normalizar_texto(cliente.get('nome')), ln=True)
    
    pdf.cell(30, 7, 'Telefone:', ln=False)
    pdf.cell(0, 7, normalizar_texto(cliente.get('telefone')), ln=True)
    
    pdf.cell(30, 7, 'Endereço:', ln=False)
    pdf.cell(0, 7, normalizar_texto(cliente.get('endereco')), ln=True)
    
    pdf.ln(5)
    
    # Dados da obra
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'DADOS DA OBRA', ln=True, fill=True)
    
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(30, 7, 'Obra:', ln=False)
    pdf.cell(0, 7, normalizar_texto(obra.get('titulo')), ln=True)
    
    pdf.cell(30, 7, 'Local:', ln=False)
    pdf.cell(0, 7, normalizar_texto(obra.get('endereco_obra')), ln=True)
    
    pdf.cell(30, 7, 'Versão:', ln=False)
    pdf.cell(0, 7, str(orcamento.get('versao', 1)), ln=True)
    
    emissao = orcamento.get('pdf_emitido_em')
    if isinstance(emissao, str):
        emissao_date = datetime.fromisoformat(emissao).date()
    elif isinstance(emissao, datetime):
        emissao_date = emissao.date()
    else:
        emissao_date = datetime.now().date()

    pdf.cell(30, 7, 'Data:', ln=False)
    pdf.cell(0, 7, emissao_date.strftime('%d/%m/%Y'), ln=True)
    
    pdf.ln(10)
    
    # Tabela de fases e serviços
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'DETALHAMENTO DO ORÇAMENTO', ln=True, fill=True)
    pdf.ln(3)
    
    for fase in fases:
        # Nome da fase
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_fill_color(200, 220, 240)
        pdf.cell(
            0,
            8,
            f"{fase['ordem']}. {normalizar_texto(fase['nome_fase'])}",
            ln=True,
            fill=True,
        )
        
        # Serviços da fase
        servicos = servicos_por_fase.get(fase['id'], [])
        
        if servicos:
            pdf.set_font('Helvetica', '', 9)
            for serv in servicos:
                servico_info = serv.get('servicos', {})
                nome = normalizar_texto(servico_info.get('nome'))
                pdf.multi_cell(0, 5, f"- {nome}")
        else:
            pdf.set_font('Helvetica', 'I', 9)
            pdf.cell(0, 6, '  Nenhum serviço cadastrado nesta fase', ln=True)
        
        # Subtotal da fase
        pdf.set_font('Helvetica', 'B', 10)
        subtotal_label = "Subtotal:"
        label_width = pdf.epw * 0.7
        value_width = pdf.epw - label_width
        line_height = 6
        label_lines = quebrar_texto_em_linhas(pdf, subtotal_label, label_width)
        start_x = pdf.l_margin
        start_y = pdf.get_y()
        for idx, line in enumerate(label_lines):
            pdf.set_xy(start_x, start_y + idx * line_height)
            pdf.cell(label_width, line_height, line, align='R')
            if idx == len(label_lines) - 1:
                pdf.set_xy(start_x + label_width, start_y + idx * line_height)
                pdf.cell(value_width, line_height, formatar_moeda(fase.get('valor_fase', 0)), align='R')
        pdf.set_y(start_y + len(label_lines) * line_height + 2)
    
    # Totais
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(26, 82, 118)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, 'RESUMO DO ORÇAMENTO', ln=True, fill=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 11)
    
    pdf.cell(130, 8, 'Valor Total:', align='R')
    pdf.cell(50, 8, formatar_moeda(orcamento.get('valor_total', 0)), align='R')
    pdf.ln()
    
    desconto = orcamento.get('desconto_valor', 0) or 0
    if desconto > 0:
        pdf.set_text_color(220, 50, 50)
        pdf.cell(130, 8, 'Desconto:', align='R')
        pdf.cell(50, 8, f"- {formatar_moeda(desconto)}", align='R')
        pdf.ln()
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_fill_color(230, 240, 230)
    pdf.cell(130, 10, 'VALOR FINAL:', align='R', fill=True)
    pdf.cell(50, 10, formatar_moeda(orcamento.get('valor_total_final', 0)), align='R', fill=True)
    pdf.ln()
    
    # Observações
    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    valido_ate = orcamento.get('valido_ate')
    if isinstance(valido_ate, str):
        valido_date = datetime.fromisoformat(valido_ate).date()
    elif isinstance(valido_ate, datetime):
        valido_date = valido_ate.date()
    else:
        valido_date = None

    if valido_date:
        dias_validade = max((valido_date - emissao_date).days, 0)
        validade_texto = (
            f"Orçamento emitido em {emissao_date.strftime('%d/%m/%Y')} "
            f"com validade até {valido_date.strftime('%d/%m/%Y')} "
            f"({dias_validade} dias)."
        )
    else:
        validade_texto = (
            f"Orçamento emitido em {emissao_date.strftime('%d/%m/%Y')}."
        )

    pdf.multi_cell(0, 5,
        f"{validade_texto}\n"
        "Condições de pagamento a combinar.\n"
        "Materiais não inclusos, salvo indicação contrária."
    )
    
    # Retorna os bytes do PDF
    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1")
    elif isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)
    return pdf_bytes
