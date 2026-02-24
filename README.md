# ⚽ Data Pipeline & Analytics para Scout Esportivo

Um pipeline de dados profissional (ETL) focado em extrair, transformar e analisar métricas avançadas de futebol. Este projeto automatiza a coleta de dados brutos de partidas e jogadores, armazenando-os em nuvem para modelagem e visualização em dashboards de Business Intelligence.

## 🎯 O Problema
No scout esportivo moderno, analisar apenas "gols e assistências" é insuficiente. É necessário entender o contexto de criação (xG, xA, passes progressivos, zonas de calor). Além disso, ferramentas de BI frequentemente quebram cálculos de médias e taxas (como *Métricas por 90 minutos*) quando os dados já vêm agregados.

## 💡 A Solução
Construção de um **Motor de Scout** em Python que se conecta a APIs esportivas para extrair exclusivamente os **dados brutos** e absolutos de cada jogador por partida. Esses dados são persistidos em um banco de dados relacional em nuvem e conectados ao Power BI, onde cálculos dinâmicos e precisos (DAX) são realizados para gerar inteligência de mercado e identificar oportunidades de contratação.

## 🛠️ Stack Tecnológica
* **Linguagem:** Python 3
* **Extração & Web Scraping:** curl_cffi (Bypass de TLS/Cloudflare), manipulação de APIs REST.
* **Banco de Dados (Cloud):** Supabase (PostgreSQL)
* **Data Viz & Analytics:** Power BI (Modelagem de Dados e DAX)
* **Controle de Ambiente:** python-dotenv

## ⚙️ Arquitetura do Projeto
1.  **Extract (Extração):** O script `motor_api.py` mapeia IDs de campeonatos e temporadas, varrendo todos os jogos concluídos para extrair estatísticas de mais de 50 variáveis diferentes (passes, finalizações, duelos físicos, conduções, etc.).
2.  **Transform (Transformação):** Limpeza de dados nulos, conversão de tipagem, padronização de posições táticas e cálculo de idades baseadas em timestamps. Remoção de médias pré-calculadas para garantir a integridade matemática no BI.
3.  **Load (Carga):** Operações de `Upsert` (Update/Insert) via API do Supabase, dividindo os dados em duas tabelas normalizadas: `jogadores` (dados estáticos) e `scout_partidas` (dados dinâmicos do jogo).

## 🚀 Como Executar

**1. Clone o repositório e instale as dependências:**
    git clone https://github.com/SEU_USUARIO/motor-scouting-python.git
    cd motor-scouting-python
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    pip install -r requirements.txt

**2. Configure as variáveis de ambiente:**
Crie um arquivo .env na raiz do projeto com suas credenciais do Supabase:
    SUPABASE_URL=sua_url_aqui
    SUPABASE_KEY=sua_key_publica_aqui

**3. Execute o motor:**
    python motor_api.py

*O menu interativo permitirá baixar um jogo específico ou uma temporada inteira (ex: Brasileirão, Premier League).*

## 📊 Visualização no Power BI
Com os dados brutos no Supabase, a conexão é feita nativamente no Power BI via PostgreSQL. 
Exemplos de métricas recriadas via DAX para precisão absoluta:
* `xA p90` (Expected Assists per 90 minutes)
* `Minutos por Participação em Gol`
* `Taxa de Conversão` e `Fator Sniper`

---
**Autor**
Desenvolvido por Eduardo Vinicius
