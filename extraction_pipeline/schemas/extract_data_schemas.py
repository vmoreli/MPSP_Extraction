import enum
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import date, time

# ---------------------------------------------------
# Enums para vocabulário controlado
# ---------------------------------------------------

class ClassificacaoCrime(str, enum.Enum):
    """Define a classificação jurídica principal do crime."""
    HOMICIDIO = "Homicídio"
    LATROCINIO = "Latrocínio (roubo seguido de morte)"
    LESAO_CORPORAL_SEGUIDA_DE_MORTE = "Lesão corporal seguida de morte"
    MORTE_A_ESCLARECER = "Morte a esclarecer / Morte suspeita"
    MORTE_SEM_INDICIO_DE_CRIME = "Morte sem indício de crime (acidental, natural, etc.)"

class ResultadoCrime(str, enum.Enum):
    """Define o resultado do crime (se foi consumado ou tentado)."""
    CONSUMADO = "Consumado"
    TENTADO = "Tentado"

class NaturezaAutoria(str, enum.Enum):
    """Define a natureza da autoria do crime investigado."""
    CONHECIDA = "Conhecida"
    DESCONHECIDA = "Desconhecida"


class Pessoa(BaseModel):
    """Informações sobre uma pessoa envolvida no inquérito."""
    nome: Optional[str]                     = Field(None, description="Nome da pessoa")
    cor: Optional[str]                      = Field(None, description="Cor da pessoa")
    sexo: Optional[str]                     = Field(None, description="Gênero da pessoa. Infira pelo nome quando o gênero não for citado explicitamente")
    é_policial: bool                        = Field(False, description="Indica se a pessoa é policial (True) ou não (False)")
    corporacao_policial: Optional[str]      = Field(None, description="Corporação policial (se for policial)")
    policial_em_servico: Optional[bool]     = Field(None, description="Estava em serviço no momento da ocorrência?") 
    profissao: Optional[str]                = Field(None, description="Profissão/ocupação da pessoa")
    escolaridade: Optional[str]             = Field(None, description="Escolaridade da pessoa")
    nacionalidade: Optional[str]            = Field(None, description="Nacionalidade da pessoa")
    idade: Optional[str]                    = Field(None, description="Idade da pessoa ou faixa etária aproximada")
    antecedentes_criminais: Optional[str]   = Field(None, description="Antecedentes criminais da pessoa. Não preencha com informações contextuais, como 'uso de bebida alcoólica'")

    @model_validator(mode="after")
    def validar_policial(self):
        """Garante integridade entre 'e_policial', 'corporacao_policial' e 'policial_em_servico'."""
        
        if self.é_policial:
            if not self.corporacao_policial:
                raise ValueError("Se 'e_policial=True', 'corporacao_policial' deve ser preenchida.")
        else:
            # Se não é policial, não deve ter informações de corporação
            self.corporacao_policial = None
            self.policial_em_servico = None

        return self

# ---------------------------------------------------
# Classe 'Vitima' que herda de 'Pessoa'
# ---------------------------------------------------
class Vitima(Pessoa):
    """Informações detalhadas sobre uma vítima, que é um tipo de Pessoa."""
    armada: bool                          = Field(False, description="Indica se a vítima estava armada (True) ou não (False)")
    arma_da_vítima: Optional[str]         = Field(None, description="Indica qual a arma da vítima no momento da ocorrência")
    faleceu: bool                         = Field(False, description="Indica se a vítima faleceu ou não")
    causa_juridica_da_morte: Optional[str]= Field(None, description="Causa jurídica da morte conforme tipificação inicial (ex: 'homicídio por arma de fogo', 'traumatismo cranioencefálico por espancamento')")
    relacao_vitima_autor: Optional[str]   = Field(None, description="Relação entre vítima e autor")

    @model_validator(mode="after")
    def validar_consistencia(self):
        """Garante a consistência entre campos condicionais da vítima."""
        
        # Validação da morte
        if self.faleceu:
            if not self.causa_juridica_da_morte:
                raise ValueError("Se 'faleceu=True', o campo 'causa_juridica_da_morte' deve ser preenchido.")
        else:
            # Se a vítima não faleceu, a causa da morte deve ser nula.
            self.causa_juridica_da_morte = None

        # Validação da arma
        if self.armada:
            if not self.arma_da_vítima:
                raise ValueError("Se 'armada=True', o campo 'arma_da_vítima' deve ser preenchido.")
        else:
            # Se a vítima não estava armada, a descrição da arma deve ser nula.
            self.arma_da_vítima = None
            
        return self

# ---------------------------------------------------
# 'Vitimas' usa a classe 'Vitima'
# ---------------------------------------------------
class Vitimas(BaseModel):
    """Lista de pessoas identificadas como vítimas no inquérito policial arquivado."""
    vitimas: Optional[List[Vitima]] = Field(None, description="Lista de vítimas") 

class Suspeitos(BaseModel):
    """Lista de pessoas investigadas ou apontadas como possíveis autoras dos fatos no inquérito policial arquivado."""
    Suspeitos: Optional[List[Pessoa]] = Field(None, description="Lista de autores") 

class Testemunhas(BaseModel):
    """Lista de pessoas identificadas como testemunhas no inquerito policial aquivado."""
    testemunhas: Optional[List[Pessoa]] = Field(None, description="Lista de testemunhas") 



# ---------------------------------------------------
# Schema 'Inquerito' 
# ---------------------------------------------------

class Inquerito(BaseModel):
    """Informações estruturadas sobre a ocorrência descrita no inquérito policial."""
    
    # --- Nova Seção de Classificação do Crime ---
    classificacao_crime: ClassificacaoCrime                         = Field(None, description="Classificação jurídica principal do fato.")
    resultado: Optional[ResultadoCrime]                             = Field(None, description="Resultado do crime (Consumado ou Tentado).")
    é_feminicidio: bool                                             = Field(False, description="Marque True se o crime for classificado como feminicídio (qualificadora do homicídio).")
    
    # --- Campos de Contexto ---
    data_ocorrencia: Optional[str]                                  = Field(None, description="Data da ocorrência") 
    hora_ocorrencia: Optional[str]                                  = Field(None, description="Hora da ocorrência") 
    data_registro: Optional[str]                                    = Field(None, description="Data do registro da ocorrência") 
    delegacia_registro: Optional[str]                               = Field(None, description="Nome da delegacia ou unidade policial que registrou a ocorrência.")
    
    # --- Campos de Localização
    tipo_de_local: Optional[str]                                    = Field(None, description="Tipo de local (ex: 'Residência', 'Via pública', 'Estabelecimento comercial').")
    local_detalhado: Optional[str]                                  = Field(None, description="Detalhe do local específico da ocorrência (ex: 'quarto', 'calçada', 'dentro do veículo').")
    latitude: Optional[float]                                       = Field(None, description="Latitude do local da ocorrência.")
    longitude: Optional[float]                                      = Field(None, description="Longitude do local da ocorrência.")
    municipio: Optional[str]                                        = Field(None, description="Município onde a ocorrência se deu.")
    
    # --- Campos do Modus Operandi e Evidências ---
    tipo_de_acao: Optional[str]                                     = Field(None, description="Modus operandi ou tipo de ação principal (ex: 'disparos de arma de fogo', 'espancamento', 'asfixia', 'ataque com arma branca').")
    arma_utilizada: Optional[str]                                   = Field(None, description="Tipo de arma empregada pelo autor (ex: 'revólver calibre 38', 'faca de cozinha', 'pedaço de madeira').")
    bem_roubado: Optional[str]                                      = Field(None, description="Descrição do bem subtraído, relevante para casos de latrocínio.")
    
    # --- Campos do Andamento do Inquérito ---
    natureza_da_autoria: Optional[NaturezaAutoria]                  = Field(None, description="Natureza da autoria (ex: 'Conhecida', 'Desconhecida').")
    pericia_realizada: Optional[bool]                               = Field(None, description="Indica se foi realizada perícia no local ou em armas.") 
    prisao_em_flagrante: Optional[bool]                             = Field(None, description="Indica se houve prisão em flagrante.") 
    razao_arquivamento: Optional[str]                               = Field(None, description="Razão do arquivamento, trecho exatamente como está escrito no documento original.")


    @model_validator(mode="after")
    def validar_consistencia_crime(self):
        """Garante a consistência lógica entre a classificação, resultado e qualificadoras do crime."""
        
        # Se não há classificação, não há o que validar.
        if not self.classificacao_crime:
            return self

        # Regra 1: Feminicídio é uma qualificadora do Homicídio.
        if self.é_feminicidio and self.classificacao_crime != ClassificacaoCrime.HOMICIDIO:
            raise ValueError("Feminicídio só pode ser qualificado em um crime de Homicídio.")

        # Regra 2: Latrocínio é sempre consumado (pois a morte ocorreu) e deve ter um bem roubado.
        if self.classificacao_crime == ClassificacaoCrime.LATROCINIO:
            if self.resultado == ResultadoCrime.TENTADO:
                raise ValueError("Latrocínio (roubo seguido de morte) é, por definição, um crime consumado.")
            self.resultado = ResultadoCrime.CONSUMADO # Auto-corrige para consumado
            if not self.bem_roubado:
                raise ValueError("Para o crime de Latrocínio, o campo 'bem_roubado' deve ser preenchido.")

        # Regra 3: Se não há indício de crime, não pode ser tentado/consumado nem ter qualificadoras.
        if self.classificacao_crime == ClassificacaoCrime.MORTE_SEM_INDICIO_DE_CRIME:
            self.resultado = None
            self.é_feminicidio = False
            self.bem_roubado = None
            
        return self
