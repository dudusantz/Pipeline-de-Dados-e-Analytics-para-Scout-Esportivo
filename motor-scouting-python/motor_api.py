import os
import time
from datetime import datetime
from curl_cffi import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# --- INICIALIZAÇÃO DO SUPABASE ---
load_dotenv()
url_supabase = os.environ.get("SUPABASE_URL")
key_supabase = os.environ.get("SUPABASE_KEY")

if not url_supabase or not key_supabase:
    print("❌ ERRO: Variáveis SUPABASE_URL ou SUPABASE_KEY não encontradas no arquivo .env!")
    exit()

supabase: Client = create_client(url_supabase, key_supabase)


def obter_dados_nascimento(timestamp):
    if not timestamp: return None, 0
    try:
        nascimento = datetime.fromtimestamp(timestamp)
        data_nasc_str = nascimento.strftime('%Y-%m-%d')
        hoje = datetime.now()
        idade_calc = hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
        return data_nasc_str, idade_calc
    except: return None, 0

def traduzir_pe(foot):
    if not foot: return "N/A"
    f = str(foot).lower()
    mapa = {'left': 'Canhoto', 'right': 'Destro', 'both': 'Ambidestro'}
    return mapa.get(f, foot)

def traduzir_posicao_detalhada(sigla):
    if not sigla: return ""
    mapa = {
        'GK': 'Goleiro', 'LB': 'Lateral Esquerdo', 'RB': 'Lateral Direito', 'LWB': 'Ala Esquerdo',
        'RWB': 'Ala Direito', 'CB': 'Zagueiro', 'DM': 'Volante', 'CM': 'Meia Central',
        'LM': 'Meia Esquerda', 'RM': 'Meia Direita', 'AM': 'Meia Ofensivo', 'LW': 'Ponta Esquerda',
        'RW': 'Ponta Direita', 'ST': 'Centroavante', 'CF': 'Atacante', 'LF': 'Atacante Esquerdo', 
        'RF': 'Atacante Direito', 'DC': 'Zagueiro', 'DL': 'Lateral Esquerdo', 'DR': 'Lateral Direito',
        'DMC': 'Volante', 'MC': 'Meia Central', 'AMC': 'Meia Ofensivo', 'ML': 'Meia Esquerda', 
        'MR': 'Meia Direita', 'AML': 'Meia Ofensivo (Esq)', 'AMR': 'Meia Ofensivo (Dir)', 
        'G': 'Goleiro', 'D': 'Defensor', 'M': 'Meio-campista', 'F': 'Atacante'
    }
    return mapa.get(str(sigla).upper(), sigla)

def buscar_perfil_detalhado(player_id):
    url = f"https://api.sofascore.com/api/v1/player/{player_id}"
    try:
        resp = requests.get(url, impersonate="chrome110", timeout=10)
        if resp.status_code == 200:
            p = resp.json().get('player', {})
            pos_detalhada_lista = p.get('positionsDetailed', [])
            pos_real = ""
            secundarias = "N/A"
            
            if pos_detalhada_lista:
                pos_real = pos_detalhada_lista[0]
                if len(pos_detalhada_lista) > 1:
                    sec_nomes = [traduzir_posicao_detalhada(pos) for pos in pos_detalhada_lista[1:]]
                    secundarias = ", ".join(filter(None, sec_nomes))
            else:
                 pos_real = p.get('position', 'N/A')
            
            pe_bruto = p.get('preferredFoot') or p.get('foot')
            
            return {
                'Altura': p.get('height', 'N/A'),
                'Pe': traduzir_pe(pe_bruto),
                'Pos_Real': traduzir_posicao_detalhada(pos_real),
                'Valor': p.get('proposedMarketValue', 0),
                'Secundarias': secundarias
            }
    except: pass
    return {'Altura': 'N/A', 'Pe': 'N/A', 'Pos_Real': 'N/A', 'Valor': 0, 'Secundarias': 'N/A'}

def buscar_dados_sofascore(event_id):
    url_event = f"https://api.sofascore.com/api/v1/event/{event_id}"
    resp_event = requests.get(url_event, impersonate="chrome110", timeout=15)
    if resp_event.status_code != 200: 
        raise Exception(f"Erro na API ao buscar evento: Status {resp_event.status_code}")
    
    dados_event = resp_event.json()['event']
    campeonato = dados_event['tournament']['name']
    confronto = f"{dados_event['homeTeam']['name']} x {dados_event['awayTeam']['name']}"
    ano_temporada = dados_event.get('season', {}).get('year', 'N/A')
    
    url_lineups = f"https://api.sofascore.com/api/v1/event/{event_id}/lineups"
    resp_lineups = requests.get(url_lineups, impersonate="chrome110", timeout=15)
    if resp_lineups.status_code != 200:
        raise Exception("Erro ao buscar as escalações (lineups).")
        
    dados_lineups = resp_lineups.json()
    
    lista_jogadores = []
    lista_partidas = []
    
    def processar_equipa(lado, nome_time):
        if lado not in dados_lineups: return
        elenco = dados_lineups[lado].get('players', []) + dados_lineups[lado].get('substitutes', [])
        
        for p_node in elenco:
            p_info = p_node['player']
            stats = p_node.get('statistics', {})
            minutos = stats.get('minutesPlayed', 0)
            
            if minutos > 0:
                print(f"🔎 Processando KPIs brutos: {p_info['name']}...", end=" ", flush=True)
                bio = buscar_perfil_detalhado(p_info.get('id'))
                
                pos_tatica_jogo = p_node.get('position', '')
                pos_final = traduzir_posicao_detalhada(pos_tatica_jogo) if pos_tatica_jogo else bio['Pos_Real']
                print(f"[{pos_final}] OK")
                
                # --- VARIÁVEIS BRUTAS ---
                xg = float(stats.get('expectedGoals', 0))
                xa = float(stats.get('expectedAssists', 0))
                xgot = float(stats.get('expectedGoalsOnTarget', 0))
                gols = stats.get('goals', 0)
                gols_penalti = stats.get('penaltyScore', 0)
                
                assists = stats.get('assists', stats.get('goalAssist', 0))
                chutes_gol = stats.get('shotsOnTarget', stats.get('onTargetScoringAttempt', 0))
                chutes_fora = stats.get('shotsOffTarget', stats.get('shotOffTarget', 0))
                chutes_bloq = stats.get('blockedShots', stats.get('blockedScoringAttempt', 0))
                total_chutes = chutes_gol + chutes_fora + chutes_bloq
                
                big_chances_created = stats.get('bigChancesCreated', stats.get('bigChanceCreated', 0))
                grandes_chances_perdidas = stats.get('bigChanceMissed', 0)
                passes_decisivos = stats.get('keyPasses', stats.get('keyPass', 0))
                dribles_certos = stats.get('successfulDribbles', stats.get('dribbleSucc', 0))
                perdas = stats.get('possessionLost', stats.get('possessionLostCtrl', 0))
                passes_certos = stats.get('accuratePasses', stats.get('accuratePass', 0))
                passes_tentados = stats.get('totalPasses', stats.get('totalPass', 0))
                cruz_certos = stats.get('accurateCrosses', stats.get('accurateCross', 0))
                cruz_tentados = stats.get('totalCrosses', stats.get('totalCross', 0))
                longos_certos = stats.get('accurateLongBalls', 0)
                longos_tentados = stats.get('totalLongBalls', 0)
                passes_terco_final = stats.get('accurateFinalThirdPasses', 0)
                
                desarmes = stats.get('tackles', stats.get('challengeWon', 0))
                last_man_tackle = stats.get('lastManTackle', 0)
                interceptacoes = stats.get('interceptions', stats.get('interceptionWon', 0))
                recuperacoes = stats.get('ballRecovery', 0)
                cortes = stats.get('clearances', stats.get('totalClearance', 0))
                bloqueios = stats.get('blockedScoringAttempt', stats.get('outfielderBlock', 0))
                aereo_ganhos = stats.get('aerialDuelsWon', stats.get('aerialWon', 0))
                
                faltas_cometidas = stats.get('fouls', 0)
                amarelos = stats.get('yellowCards', 0)
                vermelhos = stats.get('redCards', 0)
                penaltis_perdidos = stats.get('penaltyMiss', 0)
                erros_fatais = stats.get('errorLeadToGoal', 0) + stats.get('errorLeadToShot', 0)
                driblado = stats.get('dribbledPast', 0)
                defesas = stats.get('saves', 0)
                gols_sofridos = stats.get('goalsConceded', 0)
                nota = float(stats.get('rating', 0))

                dominios_malsucedidos = stats.get('poorControl', stats.get('unsuccessfulTouches', 0))
                conducoes = stats.get('totalCarries', stats.get('carries', 0))
                distancia_conducao = float(stats.get('totalCarryDistance', 0))
                progressao_total = float(stats.get('progressiveCarryDistance', 0))
                duelos_chao_ganhos = stats.get('groundDuelsWon', max(0, stats.get('duelWon', 0) - aereo_ganhos))
                defesas_dentro_area = stats.get('savedShotsFromInsideTheBox', stats.get('savesFromInsideBox', 0))
                socos = stats.get('punches', 0)
                
                data_nascimento, idade_calc = obter_dados_nascimento(p_info.get('dateOfBirthTimestamp'))
                valor = float(bio['Valor']) if str(bio['Valor']).isdigit() else 0.0
                
                # Campos calculados básicos de volume que não interferem nas agregações
                passes_errados = passes_tentados - passes_certos
                passes_curtos = max(0, passes_tentados - cruz_tentados - longos_tentados)
                assistencias_desperdicadas = max(0, big_chances_created - assists)

                lista_jogadores.append({
                    "id_jogador": p_info.get('id'),
                    "nome": p_info['name'],
                    "data_nascimento": data_nascimento,
                    "altura": bio['Altura'],
                    "pe": bio['Pe'],
                    "posicao_perfil": bio['Pos_Real'],
                    "secundarias": bio['Secundarias']
                })

                lista_partidas.append({
                    "id_jogo": event_id,
                    "ano_temporada": str(ano_temporada),
                    "id_jogador": p_info.get('id'),
                    "campeonato": campeonato,
                    "confronto": confronto,
                    "time_jogador": nome_time,
                    "posicao_jogo": pos_final,
                    "valor_mercado": valor,
                    "minutos": minutos,
                    "nota": nota,
                    
                    # --- ATAQUE E FINALIZAÇÃO ---
                    "gols": gols,
                    "gols_penalti": gols_penalti,
                    "gols_sem_penalti": gols - gols_penalti,
                    "xg": round(xg, 2),
                    "xgot": round(xgot, 2),
                    "chutes_no_gol": chutes_gol,
                    "chutes_fora": chutes_fora,
                    "chutes_bloq": chutes_bloq,
                    "finalizacoes_totais": total_chutes,
                    "grandes_chances_perdidas": assistencias_desperdicadas, # Mapeado para chances desperdiçadas pelo jogador
                    
                    # --- CRIAÇÃO E PASSES ---
                    "assistencias": assists,
                    "xa": round(xa, 2),
                    "grandes_chances_criadas": big_chances_created,
                    "passes_decisivos": passes_decisivos,
                    "passes_tentados": passes_tentados,
                    "passes_certos": passes_certos,
                    "passes_errados": passes_errados,
                    "saldo_passes": passes_certos - passes_errados,
                    "passes_curtos": passes_curtos,
                    "cruzamentos_tentados": cruz_tentados,
                    "cruzamentos_certos": cruz_certos,
                    "lancamentos_tentados": longos_tentados,
                    "lancamentos_certos": longos_certos,
                    "passes_terco_final": passes_terco_final,
                    
                    # --- POSSE E MOVIMENTAÇÃO ---
                    "dribles_certos": dribles_certos,
                    "posse_perdida": perdas,
                    "dominios_malsucedidos": dominios_malsucedidos,
                    "conducoes": conducoes,
                    "distancia_conducao": distancia_conducao,
                    "progressao_total": progressao_total,
                    
                    # --- DEFESA E DUELOS ---
                    "desarmes": desarmes,
                    "desarme_ultimo_homem": last_man_tackle,
                    "interceptacoes": interceptacoes,
                    "cortes": cortes,
                    "bloqueios": bloqueios,
                    "recuperacoes": recuperacoes,
                    "posse_ganha": recuperacoes,
                    "duelos_chao_ganhos": duelos_chao_ganhos,
                    "duelos_aereos_ganhos": aereo_ganhos,
                    "faltas_cometidas": faltas_cometidas,
                    "faltas_sem_cartao": max(0, faltas_cometidas - amarelos - vermelhos),
                    "dribles_sofridos": driblado,
                    "falhas_fatais": erros_fatais,
                    
                    # --- GOLEIROS / OUTROS ---
                    "penaltis_perdidos": penaltis_perdidos,
                    "defesas": defesas,
                    "defesas_dentro_area": defesas_dentro_area,
                    "socos": socos,
                    "gols_sofridos": gols_sofridos
                })
                time.sleep(0.15)

    processar_equipa('home', dados_event['homeTeam']['name'])
    processar_equipa('away', dados_event['awayTeam']['name'])
    
    # --- ENVIO PARA O SUPABASE ---
    if lista_jogadores and lista_partidas:
        print("\n☁️ Salvando dados na nuvem (Supabase)...")
        supabase.table("jogadores").upsert(lista_jogadores).execute()
        supabase.table("scout_partidas").upsert(lista_partidas, on_conflict="id_jogo,id_jogador").execute()
        print("✅ Dados brutos salvos com sucesso no Banco de Dados!")

# --- MÓDULO DE AUTOMAÇÃO ---
def listar_temporadas(torneio_id):
    url = f"https://api.sofascore.com/api/v1/unique-tournament/{torneio_id}/seasons"
    try:
        resp = requests.get(url, impersonate="chrome110")
        if resp.status_code == 200:
            temporadas = resp.json().get('seasons', [])
            print("\n📅 TEMPORADAS ENCONTRADAS:")
            for t in temporadas:
                print(f"Ano: {t['year']} | ID da Temporada: {t['id']}")
            return temporadas
    except Exception as e:
        print(f"Erro ao buscar temporadas: {e}")
    return []

def extrair_temporada_completa(torneio_id, temporada_id):
    page = 0
    total_jogos_baixados = 0
    jogos_com_erro = []  
    
    print(f"\n🚀 Iniciando extração de TODOS os jogos da temporada...")
    
    while True:
        url_events = f"https://api.sofascore.com/api/v1/unique-tournament/{torneio_id}/season/{temporada_id}/events/last/{page}"
        
        try:
            resp_ev = requests.get(url_events, impersonate="chrome110", timeout=15)
            if resp_ev.status_code != 200:
                print(f"❌ Erro ao buscar página {page}.")
                break

            dados = resp_ev.json()
            jogos = dados.get('events', [])
            
            if not jogos:
                break  

            print(f"\n" + "="*40)
            print(f"📄 PROCESSANDO PÁGINA {page + 1}")
            print("="*40)

            for jogo in jogos:
                if jogo.get('status', {}).get('code') == 100:  
                    id_jogo = jogo['id']
                    nome_home = jogo['homeTeam']['name']
                    nome_away = jogo['awayTeam']['name']
                    fase_nome = jogo.get('roundInfo', {}).get('name', 'Fase/Mata-Mata')
                    
                    print(f"\n>>> Baixando [{fase_nome}]: {nome_home} x {nome_away} (ID: {id_jogo})")
                    
                    try:
                        buscar_dados_sofascore(id_jogo)
                        total_jogos_baixados += 1
                    except Exception as e:
                        print(f"⚠️ Falha no jogo {id_jogo}. Pulando... Erro: {e}")
                        jogos_com_erro.append(f"{nome_home} x {nome_away} (ID: {id_jogo})")
                    
                    time.sleep(1.5)
                else:
                    print(f"⏳ Jogo ignorado (não finalizado): {jogo['homeTeam']['name']} x {jogo['awayTeam']['name']}")

            if not dados.get('hasNextPage', False):
                break
                
            page += 1

        except Exception as e:
            print(f"❌ Erro grave na extração da temporada: {e}")
            break

    print(f"\n🏆 EXTRAÇÃO CONCLUÍDA! {total_jogos_baixados} jogos enviados ao Supabase.")
    
    if jogos_com_erro:
        print("\n" + "!"*40)
        print("⚠️ RELATÓRIO DE JOGOS PULADOS (COM ERRO):")
        for erro in jogos_com_erro:
            print(f" - {erro}")
        print("!"*40)
        print("\nVocê pode tentar baixar esses jogos manualmente depois usando a Opção 1 do menu.")

if __name__ == "__main__":
    print("========================================")
    print("🤖 MOTOR SCOUT MASTER V8 - DADOS BRUTOS")
    print("========================================")
    
    while True:
        print("\nESCOLHA UMA OPÇÃO:")
        print("1 - Baixar apenas 1 jogo (ID do Evento)")
        print("2 - Baixar uma Temporada Inteira (ID do Campeonato)")
        print("0 - Sair")
        
        opcao = input("👉 Opção: ").strip()
        
        if opcao == '0':
            break
        elif opcao == '1':
            id_j = input("\n👉 Digite o ID do Jogo: ").strip()
            if id_j.isdigit():
                print(f"\n🚀 Iniciando extração do jogo {id_j}...")
                try:
                    buscar_dados_sofascore(id_j)
                except Exception as e:
                    print(f"❌ Erro ao baixar jogo: {e}")
        elif opcao == '2':
            id_camp = input("\n👉 Digite o ID do Campeonato (Ex: Brasileirão = 325): ").strip()
            if id_camp.isdigit():
                temporadas = listar_temporadas(id_camp)
                if temporadas:
                    id_temp = input("\n👉 Digite o 'ID da Temporada' que deseja baixar: ").strip()
                    if id_temp.isdigit():
                        extrair_temporada_completa(id_camp, id_temp)
        else:
            print("❌ Opção inválida!")