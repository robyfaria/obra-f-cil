"""
Módulo de geração de PDF para orçamentos
Usa fpdf2 para gerar PDFs simples e legíveis
"""

from fpdf import FPDF
from datetime import datetime
from io import BytesIO
from typing import Optional
from pathlib import Path
from utils.auth import get_supabase_client

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
    
    pdf.cell(30, 7, 'Data:', ln=False)
    pdf.cell(0, 7, datetime.now().strftime('%d/%m/%Y'), ln=True)
    
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
            # Cabeçalho da tabela
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(70, 6, 'Serviço', border=1, fill=True)
            pdf.cell(20, 6, 'Un.', border=1, fill=True, align='C')
            pdf.cell(25, 6, 'Qtd', border=1, fill=True, align='C')
            pdf.cell(30, 6, 'Valor Un.', border=1, fill=True, align='R')
            pdf.cell(35, 6, 'Total', border=1, fill=True, align='R')
            pdf.ln()
            
            # Linhas de serviços
            pdf.set_font('Helvetica', '', 9)
            for serv in servicos:
                servico_info = serv.get('servicos', {})
                nome = normalizar_texto(servico_info.get('nome'))
                unidade = normalizar_texto(servico_info.get('unidade'))
                
                # Trunca nome se muito longo
                if len(nome) > 35:
                    nome = nome[:32] + '...'
                
                pdf.cell(70, 6, nome, border=1)
                pdf.cell(20, 6, unidade, border=1, align='C')
                pdf.cell(25, 6, f"{serv.get('quantidade', 0):.2f}", border=1, align='C')
                pdf.cell(30, 6, formatar_moeda(serv.get('valor_unit', 0)), border=1, align='R')
                pdf.cell(35, 6, formatar_moeda(serv.get('valor_total', 0)), border=1, align='R')
                pdf.ln()
        else:
            pdf.set_font('Helvetica', 'I', 9)
            pdf.cell(0, 6, '  Nenhum serviço cadastrado nesta fase', ln=True)
        
        # Subtotal da fase
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(145, 6, f"Subtotal - {fase['nome_fase']}:", align='R')
        pdf.cell(35, 6, formatar_moeda(fase.get('valor_fase', 0)), align='R')
        pdf.ln(8)
    
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
    pdf.multi_cell(0, 5, 
        "Este orçamento tem validade de 15 dias a partir da data de emissão.\n"
        "Condições de pagamento a combinar.\n"
        "Materiais não inclusos, salvo indicação contrária."
    )
    
    # Retorna os bytes do PDF
    return pdf.output()


def salvar_pdf_storage(pdf_bytes: bytes, orcamento_id: int, obra_titulo: str) -> Optional[str]:
    """
    Salva o PDF no Supabase Storage e retorna a URL
    
    Args:
        pdf_bytes: Conteúdo do PDF
        orcamento_id: ID do orçamento
        obra_titulo: Título da obra (para nome do arquivo)
        
    Returns:
        URL pública do arquivo ou None se falhar
    """
    try:
        supabase = get_supabase_client()
        
        # Nome do arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        obra_slug = obra_titulo.lower().replace(' ', '_')[:30]
        filename = f"orcamento_{orcamento_id}_{obra_slug}_{timestamp}.pdf"
        
        # Upload para o bucket 'orcamentos'
        response = supabase.storage \
            .from_('orcamentos') \
            .upload(filename, pdf_bytes, {
                'content-type': 'application/pdf'
            })
        
        # Gera URL pública
        url = supabase.storage \
            .from_('orcamentos') \
            .get_public_url(filename)
        
        # Salva a URL no campo observacao do orçamento
        supabase.table('orcamentos') \
            .update({'observacao': f'PDF: {url}'}) \
            .eq('id', orcamento_id) \
            .execute()
        
        return url
        
    except Exception as e:
        print(f"Erro ao salvar PDF no storage: {e}")
        return None
